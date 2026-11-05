# garmintread

Läbipaistev lisakaart Garmin Treadile (ja teistele Garmini seadmetele, mis toetavad `.img` kaarte) ATV-ga sõitmiseks:
looduskaitsealade vööndid, RMK hallatav riigimaa ning pinnasteed ja rajad kogu Eesti kohta.

**Valmis kaart:** [`maps/kaitsealad_eesti.img`](maps/kaitsealad_eesti.img). Kopeeri see seadme mälukaardi kausta `garmin/`
(ära nimeta seda `gmapsupp.img`-ks, et mitte üle kirjutada olemasolevat kaarti), taaskäivita seade ja lülita
kaardikihtides sisse „Kaitsealad ja RMK – Eesti“.

## Legend

| Kaardil | Tähendus |
|---|---|
| Tumepunane tihe viirutus | Loodusreservaat |
| Punane viirutus | Sihtkaitsevöönd (looduslik) |
| Oranž viirutus | Sihtkaitsevöönd (hooldatav) |
| Kollane hõre viirutus | Piiranguvöönd |
| Tumeroheline joon | Kaitseala välispiir |
| Lilla viirutus | Hoiuala |
| Roosa viirutus | Püsielupaik |
| Tumeroosa viirutus | Üksikobjekti kaitsetsoon |
| Sinine viirutus | RMK maa (riigi katastriüksus, millel on RMK metsaeraldis) |
| Helepruun joon, tume äär | Pinnastee |
| Tumepruun katkendjoon | Rada |

Punane äärejoon tähistab reservaadi, sihtkaitsevööndi või piiranguvööndi piiri ja lilla joon hoiuala, püsielupaiga või üksikobjekti tsooni piiri. Ala nimi on kirjas ääre peal.

Kaart näitab, kus olla ettevaatlik, mitte kus tohib sõita. Iga kaitseala tegelikud piirangud on kirjas selle
kaitse-eeskirjas; kahtluse korral vaata [Keskkonnaregistrit](https://register.keskkonnaportaal.ee).

## Kaardi uuesti ehitamine

Vaja: Python 3 ja Java.

```bash
python3 -m venv .venv && .venv/bin/pip install shapely pyproj
mkdir -p tools && cd tools
curl -O https://www.mkgmap.org.uk/download/mkgmap-r4924.zip && unzip mkgmap-r4924.zip
curl -O https://www.mkgmap.org.uk/download/splitter-r654.zip && unzip splitter-r654.zip
cd ..

python3 fetch.py eesti                 # ~20 min, laeb WFS-ist alla (või: python3 fetch.py "Viljandi maakond")
.venv/bin/python build.py eesti        # ~3 min, teeb data/proc/eesti.osm
./make_img.sh eesti "Eesti"            # build/kaitsealad_eesti.img
```

- `fetch.py` laeb andmed Keskkonnaportaali GeoServeri WFS-teenusest (`gsavalik.envir.ee`).
- `build.py` ühendab RMK maatükid, lihtsustab kujud ja kirjutab OSM XML-i.
- `gen_style.py` genereerib mkgmapi stiili ja TYP-faili (värvid, viirutused). Värvide muutmiseks muuda seda faili.
- `make_img.sh` ehitab mkgmapiga läbipaistva kaardi (family ID 7337); suur sisend jagatakse enne splitteriga tükkideks.

Märkus: Tread joonistab ainult Garmini standardseid ala- ja joonetüüpe; TYP-fail muudab nende värvi.

## Andmeallikad

- Kaitsealad, vööndid, hoiualad, püsielupaigad: Keskkonnaregister (EELIS), Keskkonnaagentuur
- Katastriüksused ja omandivorm: Maa- ja Ruumiamet, katastriandmed
- RMK metsaeraldised: Metsaregister, Keskkonnaagentuur
- Pinnasteed ja rajad: Maa- ja Ruumiamet, ETAK

Andmed on seisuga 05.11.2026.
