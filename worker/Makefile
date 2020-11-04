user = cellprofiler
project = distributed-cellprofiler
tag = 2.0.0_4.0.6

.DEFAULT_GOAL: build
build:
	docker build -t $(user)/$(project):$(tag) . 
	docker login -u $(user)
	docker push $(user)/$(project):$(tag)
	echo "Your new docker registry is ready at: $(user)/$(project):$(tag)"

