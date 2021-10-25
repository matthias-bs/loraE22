#!/usr/bin/env python3
###############################################################################
# Python Script to convert LoRa range test CSV data to KML 
#
# The output file provides the RSSI value as extended data to be
# displayed with the elevation plot in GoogleEarth.
#
# Expected input format:
# <timestamp>,<latitude>,<longitude>,<altitude>,<lora_rssi>
#
# Example:
# 2021-10-18T15:59:45.889Z,52.00000° N,10.50000° E,55.5,-17
#
# Output Format:
# cf.
# https://developers.google.com/kml/documentation/kmlreference?csw=1#trackexample
#
#
# Copyright (C) 10/2021 Matthias Prinke
# 
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# created: 10/2021
#
# History:
#
# 20211018 initial release
#
######################################################################
import csv
import sys

kml_header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <name>GPS device</name>
    <!-- <Snippet>Created Wed Jun 2 15:33:39 2010</Snippet> -->

    <!-- Normal track style -->
    <Style id="track_n">
      <IconStyle>
        <scale>.5</scale>
        <Icon>
          <href>http://earth.google.com/images/kml-icons/track-directional/track-none.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <scale>0</scale>
      </LabelStyle>

    </Style>
    <!-- Highlighted track style -->
    <Style id="track_h">
      <IconStyle>
        <scale>1.2</scale>
        <Icon>
          <href>http://earth.google.com/images/kml-icons/track-directional/track-none.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <StyleMap id="track">
      <Pair>
        <key>normal</key>
        <styleUrl>#track_n</styleUrl>
      </Pair>
      <Pair>
        <key>highlight</key>
        <styleUrl>#track_h</styleUrl>
      </Pair>
    </StyleMap>
    <!-- Normal multiTrack style -->
    <Style id="multiTrack_n">
      <IconStyle>
        <Icon>
          <href>http://earth.google.com/images/kml-icons/track-directional/track-0.png</href>
        </Icon>
      </IconStyle>
      <LineStyle>
        <color>99ffac59</color>
        <width>6</width>
      </LineStyle>

    </Style>
    <!-- Highlighted multiTrack style -->
    <Style id="multiTrack_h">
      <IconStyle>
        <scale>1.2</scale>
        <Icon>
          <href>http://earth.google.com/images/kml-icons/track-directional/track-0.png</href>
        </Icon>
      </IconStyle>
      <LineStyle>
        <color>99ffac59</color>
        <width>8</width>
      </LineStyle>
    </Style>
    <StyleMap id="multiTrack">
      <Pair>
        <key>normal</key>
        <styleUrl>#multiTrack_n</styleUrl>
      </Pair>
      <Pair>
        <key>highlight</key>
        <styleUrl>#multiTrack_h</styleUrl>
      </Pair>
    </StyleMap>
    <!-- Normal waypoint style -->
    <Style id="waypoint_n">
      <IconStyle>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/pal4/icon61.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <!-- Highlighted waypoint style -->
    <Style id="waypoint_h">
      <IconStyle>
        <scale>1.2</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/pal4/icon61.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <StyleMap id="waypoint">
      <Pair>
        <key>normal</key>
        <styleUrl>#waypoint_n</styleUrl>
      </Pair>
      <Pair>
        <key>highlight</key>
        <styleUrl>#waypoint_h</styleUrl>
      </Pair>
    </StyleMap>
    <Style id="lineStyle">
      <LineStyle>
        <color>99ffac59</color>
        <width>6</width>
      </LineStyle>
    </Style>
    <Schema id="schema">
      <gx:SimpleArrayField name="rssi" type="int">
        <displayName>RSSI (dBm)</displayName>
      </gx:SimpleArrayField>
    </Schema>
    <Folder>
      <name>Tracks</name>
      <Placemark>"""
        
kml_footer = """        </gx:Track>
      </Placemark>
    </Folder>
  </Document>
</kml>
"""

when = ""
coord = ""
data = """          <ExtendedData>
            <SchemaData schemaUrl="#schema">
              <gx:SimpleArrayData name="rssi">
"""

if len(sys.argv) == 1:
    print("No input file specified!", file=sys.stderr)
    exit(1)
    
print(kml_header)

with open(sys.argv[1]) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        if line_count == 0:
            pass
        else:
            when += "          <when>{}</when>\n".format(row[0])
            lat = row[1]
            ns  = lat[-1]
            lat = lat[:-3]
            if ns == 'S':
                lat = '-' + lat
            lon = row[2]
            ew  = lon[-1]
            lon = lon[:-3]
            if ew == 'W':
                lon = '-' + lon
            alt = row[3]
            coord += "          <gx:coord>{} {} {}</gx:coord>\n".format(lon, lat, alt)
            data  += "                <gx:value>{}</gx:value>\n".format(row[4])
        line_count += 1

data += """              </gx:SimpleArrayData>
            </SchemaData>
          </ExtendedData>"""
print("        <name>{}</name>".format(sys.argv[1]))
print("        <styleUrl>#multiTrack</styleUrl>")
print("        <gx:Track>")
print(when)
print(coord)
print(data)
print(kml_footer)
