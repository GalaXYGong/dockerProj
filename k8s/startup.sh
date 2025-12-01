#!/bin/bash
list="mongodb.yml", "mysql.yml", "storage.yml", "processing.yml", "auth-service.yml", "data_entry_web.yml", "api-gateway.yml"
for file in $list
do
    echo "start applying $file ..."
    kubectl apply -f $file
    echo "Applied $file"
    sleep 5
done
echo "All Kubernetes configurations have been applied."
echo "You can check the status of the pods using 'kubectl get pods'."
echo "checking pods status ..."
function check_pods_status() {
    pending_pods=$(kubectl get all | grep -c "pending")
    if [ "$pending_pods" -gt 0 ]; then
        echo "There are still $pending_pods pending pods. Waiting for 10 seconds before rechecking..."
        sleep 10
        check_pods_status
    else
        echo "All pods are running."
        echo "the external IP of api-gateway is :"
        echo $text | cut -d " " -f4
    fi
}
check_pods_status