# pyright: reportMissingTypeStubs=true
from pathlib import Path

import pandas as pd
import param

import visualization_tool.database.database as db
from visualization_tool.config import DATA_PATH


class Flight(param.Parameterized):
    # I initialize everything here so that those Param objects are never in an invalid state
    study_site = param.Selector(objects=db.get_study_sites(), allow_None=False)
    date = param.Selector(objects=db.get_dates(study_site.default), allow_None=False)
    camera = param.Selector(
        objects=db.get_cameras(study_site.default, date.default), allow_None=False
    )
    # Just a parameter that is toggled every time the data for the flight was updated
    # This is the parameter that should be watched by external views depending on this class.
    changed = param.Boolean(default=False, precedence=-1)

    def __init__(self):
        super().__init__()
        self._updating = False
        self.flight_id: int
        self.flight_folder: Path
        self.image_coordinates: pd.DataFrame

        self.fetch_data()  # pyright: ignore

    @param.depends("study_site", watch=True)
    def site_updated(self):
        if not self._updating:
            self._updating = True
            # Updating dates
            dates = db.get_dates(self.study_site)
            self.param["date"].objects = dates
            self.date = dates[0]

            # Updating cameras
            cameras = db.get_cameras(self.study_site, self.date)
            self.param["camera"].objects = cameras
            self.camera = cameras[0]

            self._updating = False

    @param.depends("date", watch=True)
    def date_updated(self):
        if not self._updating:
            self._updating = True
            cameras = db.get_cameras(self.study_site, self.date)
            self.param["camera"].objects = cameras
            if self.camera not in cameras:
                self.camera = cameras[0]
            self._updating = False

    # The two following methods are needed in order to only fetch data once when
    # a dropdown is changed
    @param.depends("date", "study_site", "camera", watch=True)
    def fetch_data(self):
        if not self._updating:
            res = db.get_flight_id_path(self.study_site, self.date)
            self.flight_id, self.flight_folder = res
            self.flight_folder = DATA_PATH.joinpath(self.flight_folder)
            print("FLIGHT FOLDER", self.flight_folder)
            self.image_coordinates = self.fetch_image_coordinates()
            self.changed = not self.changed  # pyright: ignore

    def fetch_image_coordinates(self) -> pd.DataFrame:
        """
        Returns the image labels and epsg:3812 (ETRS89) coordinates as a DataFrame
        The DataFrame has the following columns: ['x', 'y', 'yaw' 'label', 'id']
        """
        camera_id = db.get_camera_id(self.camera)
        result = db.get_flight_camera_image_coordinates(self.flight_id, camera_id)
        df = pd.DataFrame(result, columns=["x", "y", "yaw", "label", "id"])
        return df
