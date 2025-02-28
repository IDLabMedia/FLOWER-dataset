import sqlite3
from pathlib import Path

from visualization_tool.config import DATA_PATH, DATABASE_PATH
from visualization_tool.database.insert_image_metadata import ingest_metadata


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class _DBConnection(metaclass=Singleton):
    def __init__(self):
        self._conn: None | sqlite3.Connection = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = self.__create_connection()
            init_database()
        return self._conn

    def __create_connection(self):
        try:
            c = sqlite3.connect(DATABASE_PATH)
            print(
                f"Opened SQLite database with version {sqlite3.sqlite_version} successfully."
            )
            return c

        except sqlite3.OperationalError as e:
            print(DATABASE_PATH)
            print("Failed to open database:", e)
            raise e

    def __del__(self):
        print("Destructor of DBConnection called")
        self.conn.close()


def init_database():
    print("Initializing database...")
    conn = _DBConnection().conn
    cursor = conn.cursor()

    # Check if the database is empty
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    if len(tables) == 0:
        print("Database is empty, creating schema and ingesting metadata...")
        sqlfile = Path(__file__).parent / "create_db.sql"
        _DBConnection().conn.cursor().executescript(sqlfile.read_text())

        # Inserting the data
        ingest_metadata()

    # TODO: Check if database is complete?


## Model classes
class ImageMetadata:
    def __init__(
        self,
        id: int,
        label: str,
        flight_id: int,
        camera_id: int,
        raw_path: Path | None,
        jpg_path: Path | None,
        epsg3812_easting: float,
        epsg3812_northing: float,
        altitude: float,
        yaw_est: float,
    ):
        self.id = id
        self.label = label
        self.flight_id = flight_id
        self.camera_id = camera_id
        self.raw_path = raw_path
        self.jpg_path = jpg_path
        self.epsg3812_easting = epsg3812_easting
        self.epsg3812_northing = epsg3812_northing
        self.altitude = altitude
        self.yaw_est = yaw_est


#
# class FlightData:
#     def __init__(
#         self,
#         id: int,
#         study_site: str,
#         date: str,
#         camera: str,
#         path: Path,
#     ):
#         self.id = id
#         site_split = study_site.split("-")
#         self.location = site_split[0]
#         self.mow_pattern = site_split[1]
#         self.date = date
#         self.camera = camera
#         self.path = path
#


def query(sql, params=()):
    conn = _DBConnection().conn
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    data = cur.fetchall()
    cur.close()
    return data


def insert(sql, params):
    conn = _DBConnection().conn
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    cur.close()
    return cur.lastrowid


def get_study_sites():
    sql = """SELECT DISTINCT study_site FROM flights"""
    res = query(sql, ())
    return [t[0] for t in res]


def get_dates(site):
    sql = """SELECT DISTINCT date FROM flights
        WHERE study_site = ?"""
    res = query(sql, (site,))
    return [t[0] for t in res]


def get_cameras(site, date):
    sql = """SELECT DISTINCT c.name
            FROM images
            INNER JOIN flights f ON images.flight_id = f.id
            INNER JOIN cameras c ON images.camera_id = c.id
            WHERE f.study_site = ? AND f.date = ?"""
    res = query(sql, (site, date))
    return [t[0] for t in res]


def get_camera_id(camera_name: str):
    sql = """SELECT id FROM cameras WHERE name = ?"""
    return query(sql, (camera_name,))[0][0]


def get_flight_camera_image_coordinates(flight_id: int, camera_id: int):
    sql = """SELECT epsg3812_easting, epsg3812_northing, yaw, label, id
                 FROM images
                 WHERE flight_id = ? AND camera_id = ?"""
    return query(sql, (flight_id, camera_id))


def get_flight_id_path(study_site, date):
    sql = """SELECT id, path FROM flights
            WHERE study_site = ? AND date = ? """
    return query(sql, (study_site, date))[0]


def get_image(id: int) -> ImageMetadata:
    sql = """SELECT label, flight_id, camera_id, raw_path, jpg_path, epsg3812_easting, epsg3812_northing, altitude, yaw
                FROM images WHERE id=?
            """
    res = query(sql, (id,))[0]
    i = ImageMetadata(
        id=id,
        label=res[0],
        flight_id=res[1],
        camera_id=res[2],
        raw_path=DATA_PATH.joinpath(res[3]) if res[3] is not None else None,
        jpg_path=DATA_PATH.joinpath(res[4]) if res[4] is not None else None,
        epsg3812_easting=res[5],
        epsg3812_northing=res[6],
        altitude=res[7],
        yaw_est=res[8],
    )
    return i


#
# def get_flight(id: int) -> FlightData:
#     sql = """SELECT study_site, date, camera, path
#               FROM flights WHERE id=?"""
#     res = query(sql, (id,))[0]
#     return FlightData(
#         id=id,
#         study_site=res[0],
#         date=res[1],
#         camera=res[2],
#         path=DATA_PATH.joinpath(res[3]),
#     )


def update_image_paths(image_id, raw_path: Path, jpg_path: Path):
    if raw_path.is_relative_to(DATA_PATH):
        raw_path = raw_path.relative_to(DATA_PATH)

    if jpg_path.is_relative_to(DATA_PATH):
        jpg_path = jpg_path.relative_to(DATA_PATH)

    sql = """UPDATE images
            SET jpg_path = ?,
                raw_path = ?
            WHERE
                id = ? """
    return query(sql, (jpg_path.as_posix(), raw_path.as_posix(), image_id))
