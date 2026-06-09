user = estebanmiglietta
project = distributed-cellprofiler
tag = 2.2.0_4.2.8_BiosensorV1

.DEFAULT_GOAL: build
build:
	docker buildx build --platform linux/amd64 -t $(user)/$(project):$(tag) . 
	docker login -u $(user)
	docker push $(user)/$(project):$(tag)
	echo "Your new docker registry is ready at: $(user)/$(project):$(tag)"

