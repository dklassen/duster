## Introduction
This is a library used to control and record information from the SDS011 Particle Sensor from Nova Fitness. The sensor is low cost so don't expect miracles over a higher end measurement device like a [Dylos pro](http://www.dylosproducts.com/dcproairqumo.html). Measurements will correlate linearly with a more expensive unit however the accuracy of the readings cant be trusted without correction. 

Nova PM sensor SDS011 can measure fine dust and smoke = particulate matter (MP) concentrations in two categories:

- Ultrafine dust particles with a diameter of 0 – 2.5 micrometres (μm/m3).
- Fine dust particles with a diameter 2.5 – 10 micrometres (μm/m3).

I have these in my wood shop to alert me when dust collection is failing or I should put on my respirator. Hopefully this library is useful and I encourage others to contribute.

### Use

### OSX

Plug in your sensor and determine its path using `ls`:
```bash
ls /dev/cu.*
```

```python
from duster import sensor

responseHandler = sensor.ResponseHandler(
    message=sensor.ResponseMessage)

sds011 = sensor.SDS011Factory.create(
    port="/dev/cu.usbserial-1410",
    baudrate=9600,
    deviceID=b'\xff\xff',
    responseHandler=responseHandler,
    commandHandler=sensor.CommandHandler,
    )

while True:
    raw_measurement = sds011.read()
    sensor.MeasurementHandler.decode(raw_measurement)
```

## Development
Setup a virtual env and install dependencies:
> python -m venv env && python -m pip install -e .

and run tests:
> python -m pytest tests

## Contributing
We encourage contributions to this project.