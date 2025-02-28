import holoviews as hv
import panel as pn

from visualization_tool.flight import Flight
from visualization_tool.image_selector import ImageSelector
from visualization_tool.image_view import ImageView
from visualization_tool.ortho_view import OrthoView

hv.extension("bokeh")  # type: ignore

flight = Flight()
ortho_view = OrthoView(flight=flight)
image_selector = ImageSelector(flight=flight, ortho_view=ortho_view)
image_view = ImageView(flight=flight, image_selector=image_selector)

gr = pn.GridSpec(sizing_mode="scale_width", nrows=10, ncols=2)

gr[0:10, 0:1] = (ortho_view.view * image_selector.view).opts(
    framewise=True,
    data_aspect=1,
    responsive=True,
    active_tools=["wheel_zoom"],
    default_tools=["pan", "wheel_zoom", "reset"],
    xaxis="bare",
    yaxis="bare",
)

gr[0:10, 1:2] = image_view.view

app = pn.Tabs(
    (
        "Explore view",
        gr,
    )
)


pn.template.BootstrapTemplate(
    site="FLOWER",
    sidebar=[
        flight,
        ortho_view.param,
        image_selector.param,
        image_view.param,
        # ortho_view.view,
    ],
    title="Data Explorer",
    main=app,
).servable()
