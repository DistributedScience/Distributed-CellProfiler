user = bethcimini
project = cellprofiler_bugfix
tag = cp4ecs_5

.DEFAULT_GOAL: build
build:
	docker build -t $(user)/$(project):$(tag) --no-cache . 
	docker login -u $(user)
	docker push $(user)/$(project):$(tag)
	echo "Your new docker registry is ready at: $(user)/$(project):$(tag)"

