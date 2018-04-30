#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright © 2016-2018 Mohamed El Morabity
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not,
# see <http://www.gnu.org/licenses/>.

# Virtual Hard Disk Image Format Specification:
# https://technet.microsoft.com/en-us/virtualization/bb676673.aspx


'''
RAW disk image to Azure-compatible VHD conversion
=================================================

Converts a RAW disk image to an Azure-compatible VHD image. Fixed size VHDs are
generated (Azure only supports fixed-size images currently).

Many tools, like qemu-img, generate VHD files which fail on Azure because of
wrong metadata. VHD files contain metadata like the creator application; Azure
only supports VHDs with 'win ' as creator application. This script writes the
appropriate metadata for Azure on the generated VHD image.

Azure image virtual disks need to be sized to an even 1 MB boundry. It may be
necessary to resize the RAW image before converting it to VHD. Commands below
can be used to resize RAW images:

  >  rawdisk=⟨Path to the RAW disk image⟩
  >  MB=$((1024*1024))
  >  size=$(qemu-img info -f raw --output json "$rawdisk" | awk 'match($0, /"virtual-size": ([0-9]+),/, val) {print val[1]}')
  >  rounded_size=$((($size/$MB + 1)*$MB))
  >  echo "Rounded Size = $rounded_size"
  >  qemu-img resize $rawdisk $rounded_size
'''


import argparse
import os
import shutil
import struct
import uuid


def vhd_chs(size):
    """Compute the CHS from the size of a RAW image."""

    sectors = size / 512
    if sectors > 65535 * 16 * 255:
        sectors = 65535 * 16 * 255

    if sectors >= 65535 * 16 * 63:
        sectors_per_track = 255
        heads = 16
        cylinder_times_heads = sectors / sectors_per_track
    else:
        sectors_per_track = 17
        cylinder_times_heads = sectors / sectors_per_track
        heads = (cylinder_times_heads + 1023) >> 10

        if heads < 4:
            heads = 4

        if cylinder_times_heads >= heads << 10 or heads > 16:
            sectors_per_track = 31
            heads = 16
            cylinder_times_heads = sectors / sectors_per_track

        if cylinder_times_heads >= heads << 10:
            sectors_per_track = 63
            heads = 16
            cylinder_times_heads = sectors / sectors_per_track

    cylinders = cylinder_times_heads / heads

    return (cylinders, heads, sectors_per_track)


def vhd_footer_checksum(footer):
    """Compute the checksum for the footer of a VHD image."""

    checksum = sum(bytearray(footer))

    return checksum ^ 0xFFFFFFFF


def vhd_footer(raw_file_size):
    """Generate a VHD footer from the size of a RAW image."""

    vhd_footer_format = '>8sIIQI4sI4sQQHBBII16sB427s'

    cookie = 'conectix'
    features = 2
    file_format_version = 0x00010000
    data_offset = 0xFFFFFFFFFFFFFFFF
    time_stamp = 0
    creator_application = 'win '
    creator_version = 0x00060003
    creator_host_os = 'Wi2k'
    original_size = raw_file_size
    current_size = original_size
    (cylinders, heads, sectors_per_track) = vhd_chs(current_size)
    disk_type = 2
    checksum = 0
    unique_id = uuid.uuid4().bytes
    saved_state = 0
    reserved = '\0' * 427

    footer_fields = [
        cookie,
        features,
        file_format_version,
        data_offset,
        time_stamp,
        creator_application,
        creator_version,
        creator_host_os,
        original_size,
        current_size,
        cylinders,
        heads,
        sectors_per_track,
        disk_type,
        checksum,
        unique_id,
        saved_state,
        reserved
    ]
    footer_tmp = struct.pack(vhd_footer_format, *tuple(footer_fields))
    footer_fields[14] = vhd_footer_checksum(footer_tmp)
    footer = struct.pack(vhd_footer_format, *tuple(footer_fields))

    return footer


def convert(raw_file, vhd_file):
    """Generate a VHD file from a RAW image."""

    # Check if RAW image size is aligned to 1 MB
    raw_file_size = os.path.getsize(raw_file)
    if raw_file_size % (1024 * 1024) != 0:
        raise Exception('RAW image size is not aligned to 1 MB')

    with open(vhd_file, 'wb') as vhd:
        with open(raw_file, 'rb') as raw:
            shutil.copyfileobj(raw, vhd)

        footer = vhd_footer(raw_file_size)
        vhd.write(footer)


def main():
    """Main execution."""

    parser = argparse.ArgumentParser(
        description='Convert a RAW image to a fixed-size VHD image suitable for Azure'
    )
    parser.add_argument('raw_image', help='path to a RAW image file')
    parser.add_argument('vhd_image', help='path to the VHD image to generate')
    args = parser.parse_args()
    convert(args.raw_image, args.vhd_image)


if __name__ == "__main__":
    main()
