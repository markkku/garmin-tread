#!/bin/bash
# Kasutus: ./make_img.sh viljandi "Viljandimaa"   -> build/kaitsealad_viljandi.img
#          ./make_img.sh eesti "Eesti"            -> build/kaitsealad_eesti.img
# Suur sisend jagatakse splitteriga tükkideks, väike läheb otse mkgmapi.
set -e
slug=$1; area=$2
cd "$(dirname "$0")"
root=$PWD
python3 gen_style.py
rm -rf build/$slug && mkdir -p build/$slug && cd build/$slug

osm=$root/data/proc/$slug.osm
size=$(stat -c %s "$osm")
if [ "$size" -gt 50000000 ]; then
  java -Xmx4g -jar "$root"/tools/splitter-r654/splitter.jar \
    --mapid=73370001 --max-nodes=1000000 --output-dir=tiles "$osm"
  inputs=(-c tiles/template.args)
else
  inputs=(--mapname=73370001 "$osm")
fi

java -Xmx4g -jar "$root"/tools/mkgmap-r4924/mkgmap.jar \
  --style-file="$root"/style --style=tsoonid \
  --family-id=7337 --product-id=1 \
  --family-name="Kaitsealad ja RMK" --series-name="Kaitsealad ja RMK" \
  --description="Kaitsealad ja RMK - $area" --area-name="$area" \
  --overview-mapname=73370000 \
  --code-page=1252 --lower-case --transparent --draw-priority=28 --gmapsupp \
  "${inputs[@]}" "$root"/style/tsoonid.txt
cp gmapsupp.img ../kaitsealad_$slug.img
ls -la ../kaitsealad_$slug.img
