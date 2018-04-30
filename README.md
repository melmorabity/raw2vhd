RAW disk image to Azure-compatible VHD conversion
=================================================

Converts a RAW disk image to an Azure-compatible VHD image. Fixed size VHDs are generated (Azure only supports fixed-size images currently).

Many tools, like qemu-img, generate VHD files which fail on Azure because of wrong metadata. VHD files contain metadata like the creator application; Azure only supports VHDs with 'win ' as creator application. This script writes the appropriate metadata for Azure on the generated VHD image.

Azure image virtual disks need to be sized to an even 1 MB boundry. It may be necessary to resize the RAW image before converting it to VHD. Commands below can be used to resize RAW images:

```
  >  rawdisk=⟨Path to the RAW disk image⟩
  >  MB=$((1024*1024))
  >  size=$(qemu-img info -f raw --output json "$rawdisk" | awk 'match($0, /"virtual-size": ([0-9]+),/, val) {print val[1]}')
  >  rounded_size=$((($size/$MB + 1)*$MB))
  >  echo "Rounded Size = $rounded_size"
  >  qemu-img resize $rawdisk $rounded_size
```