# FLOWER: data explorer

This visualization tool is made in Python. It uses the HoloViz tools to create an interactive web based data explorer.

You need Python 3.12 or higher to run this tool. To install the dependencies we use Poetry, you can find instruction for installing poetry [here](https://python-poetry.org/docs/#installation).

Once Poetry is installed, you can install the dependencies by running the following command from the visualization_tool directory:

```bash
poetry install
```

Before running the visualization tool you need to configure the dataset path. Change the value of the `DATASET_PATH` variable in the `src/visualization_tool/config.py` file to the root path of the downloaded dataset. This folder should thus contain folders being the location (Waarmaarde, Muziekbos, Palingbeek).
It is important that the dataset is structured in the same way as the downloaded dataset.  

From the visualization_tool directory, you can now run the following command to start the visualization tool:

```bash
poetry run panel serve src/visualization_tool/vistool.py

```

You can open the visualization tool by navigating to the following URL in your browser:

```url
 http://localhost:5006/vistool
```

## Database update

The database is only created and populated on the first run of the application, when no database file is found. This means that when downloading additional flights or changing the data path, the database will not be updated consequently. To update the database, you can delete the database file `metadata.db` and restart the application. The database will then be recreated and populated with the new data.
