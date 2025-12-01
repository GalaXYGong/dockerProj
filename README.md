# start all k8s services
run script `startup.sh` to start all k8s services including api-gateway, data-entry-web, auth-service, storage service etc.
```bash
./startup.sh # under k8s/ directory
```

# access api-gateway
After all services are started, you can access the api-gateway service via its external IP address. You can get the external IP address by running the following command:

```bash
kubectl get all | grep LoadBalancer | cut -d " " -f4
```

# test pages
go to `http://<EXTERNAL_IP>` to access the landing page.
user: test
password: 123
## fill in data entry form and submit
## check data listing page - dashboard

# run load test
before running test
run scrip hpa.sh to enable HPA for api-gateway deployment
It is recommended to open up jmeter GUI to monitor the load test process. don't forget to replace the EXTERNAL_IP in jmeter test 
if you don't have jmeter GUI, you can run the load test script `loadtest.sh` directly. Make sure to replace the EXTERNAL_IP variable in the script with the actual external IP address of the api-gateway service.


# watch HPA status
you can run the following command to watch the HPA status during load test:
```bash
watch kubectl get hpa,pods
```
you will see the number of pods for api-gateway deployment scale up and down based on the CPU utilization. from 2 - 5 pods。
![alt text](<Pasted image 20251130174040.png>)
after stopping the load test, you can see the HPA scales down the pods to the minimum number defined in the HPA configuration in 1 minute.
![alt text](<Pasted image 20251130174318.png>)