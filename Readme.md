
## Jupiter python notebook for datascience
e.g.  Treasury Bond yield chart

<img src=./jovyan/charts/ty_3m_5y_30y.png style="max-width:100%" />


Clone this repo on a unix/linux terminal with docker enabled.

```
git clone  <Git URL of this project> ~/workspace/kafka-notebook
```


## Build Notebook Image

```bash
#docker
docker build -t jupiter-an/notebook  ./image  
# OR docker-compose
docker-compose build notebook
```

### Run Notebook 

```bash
#docker
docker run --rm -d -p 8888:8888 \
  --name jupiter-an  \
  -v $(pwd)/jovyan:/home/jovyan \
  -v $(pwd)/data:/data \
  jupiter-an/notebook start-notebook.sh  \
  --NotebookApp.password='sha1:0b693d4b0248:a06da93936310eee98e56a09ac40cd05f496c411' \
  --NotebookApp.allow_origin='*'

# OR docker-compose

docker-compose up -d

```
Access at  http://{docker-host}:8888   . Default password is `sequence`


### Run with docker Compose

```bash
docker-compose up -d 
```
