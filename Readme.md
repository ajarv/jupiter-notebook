## Step 1 

Clone this repo on a unix/linux terminal with docker enabled.

```
git clone  <Git URL of this project> ~/workspace/kafka-notebook
```


## Build Notebook Image

```bash
docker build -t kafka-py/notebook  ./image  
```

### Run Notebook 

```bash

docker run --rm -d -p 8888:8888 --name kafka-notebook  -v $(pwd)/jovyan:/home/jovyan kafka-py/notebook start-notebook.sh  --NotebookApp.password='sha1:0b693d4b0248:a06da93936310eee98e56a09ac40cd05f496c411' --NotebookApp.allow_origin='*'

```
Access at  http://docker-host:8888   . Default password is `sequence`


### Run with docker Compose

```bash
docker-compose up -d 
```

### Access Confluent Cloud CLI
