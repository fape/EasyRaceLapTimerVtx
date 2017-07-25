# EasyRaceLapTimerVtx

use framebuffer to display [EasyRaceLapTimer](https://github.com/polyvision/EasyRaceLapTimer) monitor view

![Imgur](http://i.imgur.com/MXc51RAh.jpg)


## Usage
* VTX
  * get 4-pole 3.5mm male jack (eg [aliexpress](https://www.aliexpress.com/item/High-Quality1-8-3-5mm-4-pole-3-ring-4-way-Audio-Video-TRRS-mini-male/32240774103.html))
  * get vtx (eg [TS5823](https://www.aliexpress.com/w/wholesale-TS5823.html?site=glo&SearchText=TS5823&g=y&SortType=total_tranpro_desc&groupsort=1&tc=af&initiative_id=SB_20170724210116) or [TS5823S](https://www.aliexpress.com/w/wholesale-TS5823S.html?site=glo&SearchText=TS5823S&g=y&SortType=total_tranpro_desc&groupsort=1&tc=af&initiative_id=SB_20170724210237))
  * solder video and ground
  
  ![rpi connection](http://i.imgur.com/8RDw5qJ.png) [source](http://www.instructables.com/id/Raspberry-Pi-2-Quick-n-Easy-RCA/)
  
* Raspberry Pi
  * install packages `sudo apt-get install python python-pygame paho-mqtt python-argparse` (required internet connection)
  * force pal mode in `/boot/config.txt` and reboot (adjust last 4 values to fill the whole screen)
      ```
      sdtv_mode=2
      hdmi_ignore_hotplug=1
      overscan_scale=1
      overscan_left=8
      overscan_right=-10
      overscan_top=-13
      overscan_bottom=-15
      ```
 * download/checkout repo
 * change `BASE_URL` in `vtx.py`
 * start with`python ./vtx.py` (use json api with polling)
   * `python ./vtx.py -u` (use udp broadcast)
