# MagRSS

This project aims to recollect fingerprint data from smartphone's built-in magnetometer, GPS, and cellular Received Signal Strength (RSS) in order to train a machine learning model.

By doing a mapping between...:

```
 { Geomagnetic field strength  and Cellular signal strength }
↳{Road Lane Position a.k.a *Road* or *Sidewalk*}
```

...And training a Neural Network with the above data *(and some crowdsourcing of course!)*, we can hopefuly localize users/smartphones position relative to the road using only the latter sensors (magnetometer and cellular) without having to rely on the resource-intensive GPS module.

## Proof of concept

Have a smartphone application that logs:
+ GPS
+ Accelerometer
+ Gyroscope
+ Magnetometer
+ Cellular towers RSS

![MagRSS Proof of Concept](docs/assets/proof_of_concept_1.png)

Have the user collect and label the entries as
+ Road
+ Sidewalk

Depending on where the measurements are being taken

![Sensors output](docs/assets/tmi_plot.PNG)

The log from the sensors should provide a distinction between either of both lanes and should be suitable for labeling the entries and training a ML model.

## Usage Flow

![MagRSS usage flow](docs/assets/architecture.png)

## Android Application

![app screenshot](docs/assets/app_scrot.jpg)

The Android application will start to automatically log each of the aforementioned parameters once the 'Train' toggle is activated. When finished roaming around collecting GPS coordinates and fingerprints, the application will output a .csv file containing all collected data.

### Example training data entries (.csv)

latitude | longitude | magnetometer X | magnetometer Y | magnetometer Z | cellID001_dBm | cellID002_dBm | *cellID...* | LABEL | hour of day (HH)
-------- | --------- | -------------- | -------------- | -------------- | ------------- | ------------- | --------- | ----- | ---------
24.7893686 | 120.9950572 | 15.599999 | 15.54 | -43.02 | -85 | -80 | ... | SIDEWALK | 1700
24.789374 | 120.9950519 | 38.579998 | 15.0 | -21.06 | -85 | -80 | ... | SIDEWALK | 1700
... | ... | ... | ... | ... | ... | ... | ... | ... | ...
24.7895087 | 120.9949591 | 43.379997 | 8.4 | 8.58 | 0 | -94 | ... | ROAD | 1700
... | ... | ... | ... | ... | ... | ... | ... | ... | ...

Notice how *cellID001* does not have a measurement in all entries, this is because the smartphone won't always be attached to this Access Point for all locations where the logs are being collected.
