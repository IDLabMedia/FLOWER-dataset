CREATE TABLE flights (
  id INTEGER,
  study_site TEXT NOT NULL,
  date TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  CONSTRAINT flights_PK PRIMARY KEY (id),
  UNIQUE(study_site, date)
);

CREATE TABLE cameras (
  id INTEGER,
  name TEXT NOT NULL,
  CONSTRAINT cameras_pk PRIMARY KEY (id),
  UNIQUE(name)
);

CREATE TABLE images (
  id INTEGER,
  label TEXT NOT NULL, -- The name of the image without extension like DSC03452
  camera_id TEXT NOT NULL,
  flight_id INTEGER NOT NULL,
  raw_path TEXT,
  jpg_path TEXT,
  epsg3812_easting REAL,
  epsg3812_northing REAL,
  altitude REAL,
  yaw REAL,
  CONSTRAINT images_PK PRIMARY KEY (id),
  CONSTRAINT flight_id_FK FOREIGN KEY (flight_id) REFERENCES flights(id) ON DELETE SET NULL,
  CONSTRAINT camera_id_FK FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE SET NULL,
  UNIQUE(label, flight_id),
  UNIQUE(raw_path, jpg_path) -- One of those fields should be not null, they also both can be filled
);
