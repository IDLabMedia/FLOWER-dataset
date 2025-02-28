from pathlib import Path
from typing import cast

import pandas as pd
from tqdm.auto import tqdm

import visualization_tool.database.database as db
from visualization_tool.config import DATA_PATH


def ingest_metadata():
    """Will insert flights and image metadata in database.
    The folder structure should be as follows:
    └── Waarmaarde
        └── 20220428
            ├── block
            │   ├── canon
            │   │   └── JPG
            │   └── sony
            │       └── JPG
            └── sinus
                ├── canon
                │   └── JPG
                └── sony
                    └── JPG

    """
    # fetch all folders with flight data
    camera_paths = set()
    camera_paths.update(DATA_PATH.glob("*/*/*/sony"))
    camera_paths.update(DATA_PATH.glob("*/*/*/canon"))
    camera_paths.update(DATA_PATH.glob("*/*/*/Mavic2Pro"))
    for camera_path in tqdm(camera_paths, desc="Ingesting flights"):
        camera = camera_path.name
        study_site = (
            camera_path.parent.parent.parent.name + "-" + camera_path.parent.name
        )  # Ex. Muziekbos-block
        date = camera_path.parent.parent.name

        flight_id, camera_id = check_insert_flight_and_camera(
            camera, study_site, date, camera_path.parent
        )
        # Inserting image metadata
        insert_image_metadata(camera_path, camera_id, flight_id)

    # Adding image position data (if available)

    cur = db._DBConnection().conn.cursor()
    cur.execute("""SELECT id, path FROM flights""")
    r = cur.fetchall()
    for id, path in r:
        insert_image_positions(DATA_PATH.joinpath(path), id)

    db._DBConnection().conn.commit()


def check_insert_flight_and_camera(
    camera: str, study_site: str, date: str, flight_path: Path
) -> tuple[int, int]:
    """Checks if the flight & camera is already in the database, if not insert it. Returns the flight_id and camera_id."""
    cur = db._DBConnection().conn.cursor()

    # Inserting flight
    cur.execute(
        """SELECT * FROM flights
        WHERE study_site=? AND date=?""",
        (study_site, date),
    )
    row = cur.fetchone()

    if row is None:
        cur.execute(
            """ INSERT INTO flights(study_site, date, path)
            VALUES(?, ?, ?) """,
            (
                study_site,
                date,
                flight_path.relative_to(DATA_PATH).as_posix(),
            ),
        )
        flight_id = cast(int, cur.lastrowid)
        print("\n Inserted:", (flight_id, study_site, date, camera))
    else:
        print("\n Flight already present:", row[:4])
        flight_id = row[0]

    # Inserting camera
    cur.execute(
        """SELECT * FROM cameras
        WHERE name=?""",
        (camera,),
    )
    row = cur.fetchone()
    if row is None:
        cur.execute(
            """ INSERT INTO cameras(name)
            VALUES(?) """,
            (camera,),
        )
        camera_id = cast(int, cur.lastrowid)
    else:
        camera_id = row[0]

    cur.close()
    return flight_id, camera_id


def insert_image_metadata(camera_path: Path, camera_id: int, flight_id: int):
    cur = db._DBConnection().conn.cursor()

    # Finding & inserting raw images
    image_paths = []
    for ext in ("ARW", "DNG"):
        image_paths.extend(list(camera_path.glob(f"**/*.{ext}")))

    if len(image_paths) > 0:
        for image_path in tqdm(image_paths, desc="Ingesting RAW images"):
            label = image_path.stem

            cur.execute(
                """ INSERT INTO images(flight_id, camera_id, label, raw_path) VALUES (?, ?, ?, ?)
                    ON CONFLICT(flight_id, label) DO UPDATE SET
                    raw_path = excluded.raw_path""",
                (
                    flight_id,
                    camera_id,
                    label,
                    image_path.relative_to(DATA_PATH).as_posix(),
                ),
            )
    else:
        print(f"No 'raw' images found in {camera_path}")

    # Finding & inserting JPG images
    image_paths = []
    for ext in ("JPG", "jpg"):
        image_paths.extend(list(camera_path.glob(f"**/*.{ext}")))

    if len(image_paths) > 0:
        for image_path in tqdm(image_paths, desc="Ingesting JPG images"):
            label = image_path.stem
            # UPSERT clause: https://www.sqlite.org/lang_UPSERT.html

            cur.execute(
                """INSERT INTO images(flight_id, camera_id, label, jpg_path) VALUES(?, ?, ?, ?)
                    ON CONFLICT(flight_id, label) DO UPDATE SET
                    jpg_path = excluded.jpg_path""",
                (
                    flight_id,
                    camera_id,
                    label,
                    image_path.relative_to(DATA_PATH).as_posix(),
                ),
            )
    else:
        print(f"No JPEG images found in {camera_path}")


def insert_image_positions(flight_path: Path, flight_id: int):
    cur = db._DBConnection().conn.cursor()
    campos_files = list(flight_path.glob("CamPos*.txt"))
    print(campos_files)
    if len(campos_files) != 0:
        campos_file = campos_files[0]
        # "exact" camera positions that are generated by aligning cameras with photogrammetry
        metadata = pd.read_table(campos_file, sep=",", skiprows=1)
        # Removing the extension from the label column
        metadata["label"] = metadata["#Label"].apply(lambda n: n.split(".")[0])

        cur.executemany(
            f"""UPDATE images
                SET epsg3812_easting = ?,
                    epsg3812_northing = ?,
                    altitude = ?,
                    yaw = ?
                WHERE label = ? AND flight_id = {flight_id}""",
            metadata[["X_est", "Y_est", "Z_est", "Yaw_est", "label"]]
            .to_numpy()
            .tolist(),
        )
    else:
        print(f"\033[93m\n Warning: No camera positions found in {flight_path} \033[0m")


if __name__ == "__main__":
    ingest_metadata()
