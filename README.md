# Hildebrand-Glow-Python-Library
Python library for the Hildebran Glow UK smart meter HAN.  Interface / fixes for their API

## Installation

To run this code, you will need Python 3.6+

Clone this repo

## Configuration 

Make sure you have a working and valid account with Hildebrand and your device is working properly in the Bright APP.

You need to email Hildebrand to enable API access, once that is done you can add your info to the .hildebrand.credentials file, you can also hard code or use ENV variables.

You need to place this file in your home directory ~ equivalent.

```javascript
{
    "APP_ID" : "",
    "USERNAME" : "",
    "PASSWORD" : ""
}
```

`APP_ID` - the applicationId, this may vary but for now according to the API this is always b576fdb0-6e43-4ea4-ac75-a0fd85b0d701 

`USERNAME` - your user name

`PASSWORD` - your password 

## Running

If you call hildebrand.py directly assuming you have the correct credentials it will run through a set of test calls and return quite alot of data.

You can also call test.hildebrand.py for a short test and easy to read example.  

For more details please inspect the hildebrand.py file, it is reasonably documented and should be fairly clear. 

## Refs

Hildebrand API Docs https://docs.glowmarkt.com/GlowmarktApiDataRetrievalDocumentationIndividualUser.pdf
