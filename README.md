# student_reports
student_reports system for docker course
it is containerized so all you have to do is to run
```sh
docker-compose up -d --build
```
    and
    wait for a few seconds for all services to start.

now you can access api gateway on http://localhost:8099

If you want to bring it down, just run
```sh
docker-compose down -v 
```