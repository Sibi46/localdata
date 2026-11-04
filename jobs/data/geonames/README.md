# GeoNames administrative divisions snapshot

Downloaded 2026-10-13 from:
- https://download.geonames.org/export/dump/admin1CodesASCII.txt
- https://download.geonames.org/export/dump/admin2Codes.txt

Source: GeoNames, https://www.geonames.org/ . License: Creative Commons
Attribution 4.0, https://creativecommons.org/licenses/by/4.0/ .
Data supplied without guarantee of completeness or accuracy.

Bundled as a deterministic gzip JSON file; each row preserves source columns:
concatenated administrative code, name, ASCII name, GeoNames ID.
3,865 first-level divisions in 228 country codes; 47,642 second-level divisions
in 189 country codes. Administrative levels differ by country (province, region,
county, district, etc.); not every territory has both levels.

Snapshot SHA256: 184aa116f2f9bf16c4bd26cc3a292e7b62b08c237dea3186a235aefe2c441f76

The importer skips unknown country codes and orphan subdivisions and reports these
explicitly. It does not fabricate missing administrative levels or import postal codes.
Existing geographic names and IDs remain intact; only source IDs are attached when
an unambiguous same-parent match exists. Name collisions use a source-code suffix.
