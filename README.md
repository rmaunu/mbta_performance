# mbta_performance

This project compiles MBTA subway performance data into convenient class for
further analysis. The necessary modules are found in `mbta_performance`, and
base MBTA subway line data (in JSON data files) are in `data/lines`.

The base class to allow an MBTA analysis is
`mbta_performance.train.TrainCollection`. This class will allow the user to
download subway performance data, compiled into individual trains. These
trains can then be used for further analyses (e.g. MBTA delay announcement
responsiveness, delay magnitude prediction based on weather, etc.).

To start an analysis, simply `import mbta_performance`, and load a line:
```python
tc = mbta_performance.train.TrainCollection ()
tc.load_base_train (<data lines directory location>, <line name>)
```
The train direction can also be set by the `direction_id` tag ("0" or "1").

![image](data/example_plots/Orange_travel_time.png)

The project contains code necessary to analyze MBTA T performance. To get T
data for a desired set of dates, see `scripts/get_travel_dwell_times.py`. A
corpora of MBTA tweets can be obtained using `scripts/get_mbta_tweets.py`.
Finally, to visualize T travel time performance for the data downloaded, see
`scripts/build_trains.py`.

