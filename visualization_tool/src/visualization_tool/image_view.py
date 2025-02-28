import holoviews as hv
import numpy as np
import param
from holoviews.operation.datashader import rasterize
from PIL import Image
from turbojpeg import TJPF_RGB, TurboJPEG

import visualization_tool.database.database as db
from visualization_tool.flight import Flight
from visualization_tool.image_selector import ImageSelector


class ImageView(param.Parameterized):
    rotate_north = param.Boolean(default=False)
    crop_size = param.Integer(default=0)  # 0 means no crop

    flight = param.ClassSelector(
        class_=Flight, constant=True, precedence=-1, instantiate=False
    )
    image_selector = param.ClassSelector(
        class_=ImageSelector, constant=True, instantiate=False, precedence=-1
    )
    # image = param.ClassSelector(Image.Image, precedence=-1)
    image = param.Array(precedence=-1)
    image_metadata = param.ClassSelector(class_=db.ImageMetadata, precedence=-1)

    def __init__(self, flight: Flight, image_selector, **params):
        # Adding this constructor to enforce the flight param is passed
        super().__init__(flight=flight, image_selector=image_selector, **params)
        self.turbojpeg = TurboJPEG()

        self.image_dmap = hv.DynamicMap(callback=self.update_img_plot).opts(
            axiswise=True,
            framewise=True,
            responsive=True,
            data_aspect=1,
            active_tools=["wheel_zoom"],
            default_tools=["pan", "wheel_zoom", "reset"],
            xaxis="bare",
            yaxis="bare",
        )

    @param.depends("image_selector.image_id", watch=True)
    def update_image(self):
        image_id = self.image_selector.image_id
        self.image_metadata = db.get_image(image_id)
        jpg_path = self.image_metadata.jpg_path

        if jpg_path is not None:
            with open(jpg_path, "rb") as f:
                img = self.turbojpeg.decode(f.read(), pixel_format=TJPF_RGB)
        elif self.image_metadata.raw_path is not None:
            print("Error: image has not JPG path, loading raw files not yet supported")
        else:
            raise Exception(
                "Both the jpg & raw path is None, this shouldn't be possible..."
            )

        self.image = img

    @param.depends("image", "rotate_north", "crop_size")
    def update_img_plot(self):
        if self.image is not None:
            if self.crop_size > 0:
                img = get_central_crop(self.image, self.crop_size)
                central_crop = True
            else:
                img = self.image
                central_crop = False

            if self.rotate_north:
                img = np.array(
                    Image.fromarray(img).rotate(
                        -self.image_metadata.yaw_est, expand=True
                    )
                )

            rgb_plot = hv.RGB(
                # self.image[:, w_margin:-w_margin, :],
                img,
                name=self.image_metadata.label,
                bounds=(
                    -0.5,
                    -img.shape[0] / (img.shape[1] * 2),
                    0.5,
                    img.shape[0] / (img.shape[1] * 2),
                ),
            ).relabel(
                f"{self.flight.camera}, image label: {self.image_metadata.label}"
                + (
                    f" - central crop size: {self.crop_size}x{self.crop_size}"
                    if central_crop
                    else ""
                )
            )
            return rgb_plot
        else:
            return hv.RGB(
                np.random.randint(low=0, high=255, size=(50, 50, 3), dtype=np.uint8),
                # bounds=(0, 0, 1, 1),
            ).relabel("No image selected")

    @property
    def view(self):
        return rasterize(self.image_dmap)
