user = bethcimini
<<<<<<< Updated upstream
project = cellprofiler
tag = cp4ecs_2
=======
project = cellprofiler_bugfix
tag = cp4ecs_5
>>>>>>> Stashed changes

.DEFAULT_GOAL: build
build:
	docker build -t $(user)/$(project):$(tag) --no-cache . 
	docker login -u $(user)
	docker push $(user)/$(project):$(tag)
	echo "Your new docker registry is ready at: $(user)/$(project):$(tag)"

