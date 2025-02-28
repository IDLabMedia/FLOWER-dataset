from pathlib import Path

import holoviews as hv
import numpy as np
import panel as pn
import param
import rasterio
import rioxarray
import xarray
from holoviews.operation.datashader import rasterize

from .flight import Flight


class OrthoView(param.Parameterized):
    flight = param.ClassSelector(
        class_=Flight, constant=True, precedence=-1, instantiate=False
    )
    overview_level = param.Selector(objects=[], label="Downsample")
    ortho_path = param.ClassSelector(class_=Path, precedence=-1)
    ortho_xmin = param.Number(precedence=-1)
    ortho_ymin = param.Number(precedence=-1)
    ortho_gsd = param.Number(precedence=-1)
    # Signal, to update the ortho view
    update_ortho = param.Boolean(precedence=-1)

    def __init__(self, flight: Flight, **params):
        # Adding this constructor to enforce the flight param is passed
        super().__init__(flight=flight, **params)

        self.supress_update = False
        self.ortho_image = hv.DynamicMap(
            self.update_ortho_view,
        )

    @param.depends("overview_level", watch=True)
    def overview_level_updated(self):
        # When overview level parameter is updated, we need to reload the ortho but only if it was directly changed by the user.
        if not self.supress_update:
            self.update_ortho = not self.update_ortho

    @param.depends("flight.study_site", "flight.date", watch=True, on_init=True)
    def flight_updated(self):
        # Flight changes so we need to:
        #   - Find the ortho in the flight folder
        #   - Update the path
        #   - Get the overview levels and update the selector
        r = list(self.flight.flight_folder.glob("Ortho*.tif"))
        if len(r) > 1:
            print(
                "\033[93m\n Warning: More than one ortho found in flight folder, the first one will be selected\033[0m"
            )
        if r != []:
            # Supress orth updates, due to a change in the overview level
            self.supress_update = True
            # Ortho found
            self.ortho_path = r[0]
            src = rasterio.open(self.ortho_path, "r")
            # Check if the ortho has overviews
            self.param.overview_level.objects = [0, *src.overviews(1)]
            # By default set it on the largest available overview, so that loading is quick
            self.overview_level = self.param.overview_level.objects[-1]
            src.close()

            self.supress_update = False
        else:
            self.ortho_path = None

        self.update_ortho = not self.update_ortho

    def load_ortho(self) -> xarray.DataArray:
        if self.overview_level == 0:
            # Equivalent to "no overview", loading the highest resolution
            ortho = rioxarray.open_rasterio(self.ortho_path)
        else:
            ovli = self.param.overview_level.objects.index(self.overview_level)
            ortho = rioxarray.open_rasterio(self.ortho_path, overview_level=ovli - 1)
        assert type(ortho) is xarray.DataArray, (
            "Ortho is not an xarray.DataArray, wrong ortho loaded?"
        )
        return ortho

    ### ORTHO IMAGE
    @pn.depends("update_ortho")
    def update_ortho_view(self):
        if self.ortho_path is None:
            print("Empty ortho")
            # Hardcoded bounds to 100 so that initial scale will contain ortho, see framewise issue below
            return hv.RGB(np.zeros((2, 2, 3)), bounds=(0, 0, 100, 100))

        ortho = self.load_ortho()

        print(
            "Ortho crs: ",
            ortho.rio.crs,
        )
        if ortho.rio.crs != "EPSG:3812":
            ortho = ortho.rio.reproject("EPSG:3812")
            print("reprojected crs: ", ortho.rio.crs)

        self.ortho_gsd = ortho.rio.resolution()[0]
        print("Ortho GSD (mm/px): ", self.ortho_gsd * 1000)

        self.ortho_xmin = np.min(ortho.x.values)
        self.ortho_ymin = np.min(ortho.y.values)
        return hv.RGB(
            (
                # shifting the ortho to (0, 0) coordinate to be in frame (see framewise issue)
                ortho["x"] - self.ortho_xmin,
                ortho["y"] - self.ortho_ymin,
                ortho[0, :, :],
                ortho[1, :, :],
                ortho[2, :, :],
                ortho[3, :, :],
            ),
            vdims=list("RGB"),
        ).opts(
            title=f"{self.flight.study_site} {self.flight.date}, GSD: {self.ortho_gsd * 1000:.2f}mm/px",
        )

    @property
    def view(self):
        # Framewise issue:
        # currently rasterize prevents framewise normalization: https://github.com/holoviz/holoviews/issues/4820
        # Framewise also does not work when set on overlay objects: https://github.com/holoviz/holoviews/issues/4909
        return rasterize(self.ortho_image)
