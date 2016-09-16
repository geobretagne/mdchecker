# MDChecker

(c) GeoBretagne for the geOrchestra project

This is a simple quality assurance tool performing unit tests on a CSW-enabled catalog.
Read [INSTALL.md](./INSTALL.md) to get it work.

[GeoBretagne](http://geobretagne.fr/) uses this tool to evaluate metadatas, quick fix errors, immediately see the result and keep an eye on the catalog global score.

This tool works well with [geOrchestra SDI](http://georchestra.org). Using it with another SDI requires a little more work.


## Quick startup

Build image:
```
docker build -t geobretagne/mdchecker .
```

Run it with:
```
docker run --rm -p 8080:80 geobretagne/mdchecker
```

Finally, open [http://localhost:8080/](http://localhost:8080/) in your browser
