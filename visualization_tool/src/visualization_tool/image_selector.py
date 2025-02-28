import holoviews as hv
import param

from visualization_tool.flight import Flight
from visualization_tool.ortho_view import OrthoView


class ImageSelector(param.Parameterized):
    flight = param.ClassSelector(
        class_=Flight, constant=True, precedence=-1, instantiate=False
    )
    ortho_view = param.ClassSelector(
        class_=OrthoView, constant=True, precedence=-1, instantiate=False
    )
    selected_img_stream = param.ClassSelector(
        class_=hv.streams.Selection1D, instantiate=False, precedence=-1
    )
    image_id = param.Integer(precedence=-1)
    image_selector = param.Selector()

    def __init__(self, flight: Flight, ortho_view: OrthoView, **params):
        # adding this constructor to enforce the flight param is passed
        super().__init__(flight=flight, ortho_view=ortho_view, **params)

        self.pos_est_scatter = hv.DynamicMap(
            self.update_pos_est_scatter,
        ).opts(
            hv.opts.Points(
                size=15,
                marker="diamond",
                color="red",
                selection_color="blue",
                nonselection_alpha=1.0,
                muted_alpha=0,
                default_tools=["tap", "hover"],
            )
        )
        self.selected_img_stream = hv.streams.Selection1D(source=self.pos_est_scatter)
        self.update_image_selector()

    @param.depends("flight.changed", "ortho_view.ortho_xmin")
    def update_pos_est_scatter(self):
        # print(self.flight.image_coordinates)
        coords = self.flight.image_coordinates.dropna()

        return hv.Points(
            (
                # centering coordinates to 0, see framewise issue in OrthoView class
                coords.x - self.ortho_view.ortho_xmin,
                coords.y - self.ortho_view.ortho_ymin,
                -coords.yaw,  # we turn in goniometric direction
                coords.label,
                coords.id,
            ),
            kdims=["x", "y"],
            vdims=["yaw", "label", "id"],
            label="est_pos",
        ).opts(angle=hv.dim("yaw"))

    @param.depends("flight.changed", watch=True)
    def update_image_selector(self):
        coords = self.flight.image_coordinates
        labels = list(coords.label)
        labels.sort()
        self.param.image_selector.objects = labels

    # @pn.io.profile("selector_image_update", engine="pyinstrument")
    @param.depends("image_selector", watch=True)
    def update_image_from_selector(self):
        print("update from image selector")
        row = self.flight.image_coordinates[
            self.image_selector == self.flight.image_coordinates.label
        ]
        self.image_id = int(row.id.iloc[0])

    @param.depends("image_id", watch=True)
    def update_selector(self):
        row = self.flight.image_coordinates[
            self.flight.image_coordinates.id == self.image_id
        ]
        label = row.label.values[0]
        print(label)
        if label != self.image_selector:
            print("setting label")
            self.image_selector = label

    # @pn.io.profile("plot_stream_img_update", engine="pyinstrument")
    @param.depends("selected_img_stream.index", watch=True)
    def set_image_id(self):
        idx = self.selected_img_stream.index
        print("Image selector update triggered, image_index: ", idx)

        if idx:
            self.image_id = int(
                self.pos_est_scatter.values()[0].iloc[
                    self.selected_img_stream.index[0]
                ]["id"][0]
            )

    @property
    def view(self):
        return self.pos_est_scatter
