# student_reports
student_reports system for docker course
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
python create_table.py
python app.py
```
4. start api_gateway. start from root dir
```sh
cd api_gateway
python app.py
```
5. start auth_serivce. start from root dir
```sh
cd auth_serivce
npm install
npm start
```
6. data_service. start from root dir
```sh
cd data_service
python app.py
```
7. processing. start from root dir
```sh
cd processing
python app.py
```

now you can access api gateway on http://localhost:8099
