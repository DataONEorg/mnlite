import datetime
import dateparser
import json
import logging
from math import cos

# raise Exception("don't use this")

JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""datetime format string for generating JSON content
"""


def dtnow():
    """
    Now, with UTC timezone.

    Returns: datetime
    """
    return datetime.datetime.now(datetime.timezone.utc)


def datetimeToJsonStr(dt):
    """
    Render datetime to JSON datetime string

    Args:
        dt: datetime

    Returns: string
    """
    if dt is None:
        return None
    return dt.strftime(JSON_TIME_FORMAT)


def parseDatetimeString(ds):
    if ds is None:
        return None
    if isinstance(ds, datetime.datetime):
        return ds
    if isinstance(ds, bytes):
        ds = ds.decode("utf-8")
    return dateparser.parse(ds, settings={"RETURN_AS_TIMEZONE_AWARE": True})

class GeoBox(object):
    """
    A class to compute a bounding box from a GeoShape or GeoCoordinates.
    Latitude max and min will be used to compute the north and south bounds of the box,
    and longitude max and min will be used to compute the east and west bounds of the box.
    No Lat should exceed abs(lat) > 90, and no Lon should exceed abs(lon) > 180.

    Attributes:
        geo (dict): A dictionary representing a GeoShape or GeoCoordinates.
    
    Returns:
        A "box" string in the format "south west north east"
        where south and north are latitude values, and west and east are longitude values.
    """
    def __init__(self, geo: dict = None):
        self.L = logging.getLogger("GeoBox")
        self.geo = geo
        self.latitudes = []
        self.longitudes = []

    def set_geo(self, geo: dict):
        """
        Set the GeoShape or GeoCoordinates for the bounding box computation.

        Args:
            geo (dict): A dictionary representing a GeoShape or GeoCoordinates.
        """
        self.geo = geo    

    def compute_box(self) -> str:
        """
        Compute the bounding box from the GeoShape or GeoCoordinates.

        Returns:
            str: A string representing the bounding box in the format "south west north east".
        """
        if not self.geo:
            self.L.warning("GeoBox.compute_box called with no geo data.")
            return None

        if "latitude" in self.geo and "longitude" in self.geo:
            # GeoCoordinates are explicitly defined lat lon coordinate pairs, such as
            #   "latitude": 39.3280, "longitude": 120.1633
            self.L.debug(f"GeoBox: using latitude {self.geo['latitude']} and longitude {self.geo['longitude']}")
            self.latitudes.append(float(self.geo["latitude"]))
            self.longitudes.append(float(self.geo["longitude"]))
        if "point" in self.geo:
            # points are lat lon coordinate pairs, such as
            #   "point": "39.3280 120.1633"
            # or
            #   "point": "39.3280,120.1633"
            point: str = self.geo["point"]
            coords = point.replace(",", " ").split()
            self.L.debug(f"GeoBox: using point {coords}")
            self.latitudes.append(float(coords[0]))
            self.longitudes.append(float(coords[1]))
        if "box" in self.geo:
            # boxes are two lat lon coordinate pairs, such as
            #   "box": "39.3280 120.1633 40.445 123.7878"
            # or
            #   "box": "39.3280 120.1633,40.445 123.7878"
            box = self.geo["box"]
            coords = box.replace(",", " ").split()
            self.L.debug(f"GeoBox: using box {coords}")
            self.latitudes.extend([float(coords[0]), float(coords[2])])
            self.longitudes.extend([float(coords[1]), float(coords[3])])
        if "polygon" in self.geo or "line" in self.geo:
            # polygons and lines are comma or space-separated strings of n lat lon coordinate pairs, such as
            #   "polygon": "39.3280 120.1633 40.445 123.7878 41 121 39.77 122.42 39.3280 120.1633"
            # or
            #   "line": "39.3280 120.1633,40.445 123.7878,41 121,39.77 122.42,39.3280 120.1633"
            # they display differently but can be treated the same way for bounding box computation
            polygon = self.geo["polygon"] if "polygon" in self.geo else self.geo["line"]
            coords = polygon.replace(",", " ").split()
            self.L.debug(f"GeoBox: using polygon/line {coords}")
            for i in range(0, len(coords), 2):
                self.latitudes.append(float(coords[i]))
                self.longitudes.append(float(coords[i + 1]))
        if "circle" in self.geo:
            # A circle is the circular region of a specified radius centered at a specified latitude and longitude.
            # A circle is expressed as a pair followed by a radius in meters.
            #   "circle": "39.3280 120.1633 1000"
            circle = self.geo["circle"]
            coords = circle.replace(",", " ").split()
            self.L.debug(f"GeoBox: using circle {coords}")
            if len(coords) < 3:
                raise ValueError("Circle must have at least latitude, longitude, and radius.")
            self.latitudes.append(float(coords[0]))
            self.longitudes.append(float(coords[1]))
            radius = float(coords[2])
            # Compute the bounding box for the circle
            # The radius is in meters, so we need to convert it to degrees.
            # Approximate conversion: 1 degree latitude = 111 km, 1 degree longitude = 111 km * cos(latitude)
            lat_degree = radius / 111000  # 1 degree latitude is approximately 111 km
            lon_degree = radius / (111000 * cos(float(coords[1])))
            self.latitudes.extend([float(coords[0]) - lat_degree, float(coords[0]) + lat_degree])
            self.longitudes.extend([float(coords[1]) - lon_degree, float(coords[1]) + lon_degree])

        # If no coordinates were added, return None
        if not self.latitudes or not self.longitudes:
            self.L.warning("GeoBox.compute_box returning with no valid coordinates.")
            return None
        
        self.L.debug(f"GeoBox: latitudes {self.latitudes}")
        self.L.debug(f"GeoBox: longitudes {self.longitudes}")

        south = min(self.latitudes)
        north = max(self.latitudes)
        west = min(self.longitudes)
        east = max(self.longitudes)

        self.L.debug(f"Computed south: {south}, west: {west}, north: {north}, east: {east}")
        # Ensure the bounding box is valid
        if abs(south) > 90 or abs(north) > 90 or abs(west) > 180 or abs(east) > 180:
            self.L.warning(f"Bounding box exceeds valid bounds. SWNE: {south} {west} {north} {east}")
            return None

        return f"{south} {west} {north} {east}"

    def __str__(self):
        """
        String representation of the bounding box.

        Returns:
            str: A string representing the bounding box in the format "south west north east".
        """
        return self.compute_box()

    def __repr__(self):
        """
        String representation of the bounding box for debugging.

        Returns:
            str: A string representing the bounding box in the format "south west north east".
        """
        return f"GeoBox({self.compute_box()})"
    
    def to_dict(self):
        """
        Convert the bounding box to a dictionary format.

        Returns:
            dict: A dictionary with keys 'south', 'west', 'north', 'east'.
        """
        box = self.compute_box()
        if box is None:
            return {}
        south, west, north, east = map(float, box.split())
        return {
            "south": south,
            "west": west,
            "north": north,
            "east": east
        }
        

def convert_geoshapes_to_boxes(jld: json):
    """
    The DataONE indexing system cannot handle GeoShape types other than boxes.
    This function will convert GeoShape points, lines, and polygons,
    as well as GeoCoordinate pairs to box format in a jld JSON-LD document.

    Args:
        jld: jld dataset
    Returns: jld dataset with boxes
    """
    L = logging.getLogger("convert_geoshapes_to_boxes")

    spatial_coverage: dict = jld.get("spatialCoverage")
    if spatial_coverage is None:
        return jld
    else:
        geo = spatial_coverage.get("geo", {})
    if geo is None:
        # If there is no geo information, we can skip processing
        L.debug("No geo information found in spatialCoverage, skipping conversion.")
        return jld

    # Ensure spatial_coverage is a list for uniform processing
    if not isinstance(geo, list):
        geo = [geo]

    box = GeoBox()
    for loc in geo:
        if isinstance(loc, dict):
            box.set_geo(loc)
            box_str = box.compute_box()
            if box_str:
                loc["@type"] = "GeoShape"
                # Update the loc with the computed box
                loc["box"] = box_str
            else:
                # If no valid box could be computed, we can either skip this entry or handle it as needed
                L.debug("GeoBox.compute_box returned None, skipping this geo entry.")
                continue
            # Remove other geo properties that are not boxes
            for key in list(loc.keys()):
                if (key not in ["box"]) and (key not in ["@type"]):
                    del loc[key]
        else:
            # If the geo entry is not a dict, we can skip it or handle it as needed
            continue
    if geo == {}:
        # If geo is empty after processing, remove it from spatialCoverage
        del spatial_coverage["geo"]

    return jld
