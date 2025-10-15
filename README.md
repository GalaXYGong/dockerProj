# student_reports
student_reports system for docker course
>[!important]
>
>it is recommended that you start a virtual environment to run it.
>```sh
>python3 -m venv env
>source env/bin/activate
>```
1. install all dependencies under root dir 
```sh
pip install -r requirements.txt 
```
2. run mongo and mysql db in containers. Under root dir
```sh
docker compose up -d
```
3. start storage
```sh
cd storage
python create_tables.py
python app.py
```
4. start api_gateway. start from root dir
```sh
cd api_gateway
python gateway.py
```
5. start auth_serivce. start from root dir
```sh
cd auth_service
npm install
npm start
```
6. data_service. start from root dir
```sh
cd data_entry_web
python app.py
```
7. processing. start from root dir
```sh
cd processing
python app.py
```

now you can access api gateway on http://localhost:8099
