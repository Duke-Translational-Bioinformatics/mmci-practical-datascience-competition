# mmci-practical-datascience-competition
Djano + Angular (1.0) SPA to facilitate the machine learning competition on Microsoft Azure Machine Learning Studio

## Docker
We deploy using `docker`. First, we build the image:

```
docker build -t mmci .
```
 Next, we start the container:
```
#Background
docker run -d \
--env-file=production.env \
-p 8000:8000 \
-v $(pwd):/mmci-practical-datascience-competition \
--restart always \
mmci 
  
#Interactive
docker run -it \
--env-file=production.env \
-p 8000:8000 \
-v $(pwd):/mmci-practical-datascience-competition \
mmci bash 
```