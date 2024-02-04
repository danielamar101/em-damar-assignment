
run:
	python main.py

build:
	pip install -r requirements.txt

build_image:
	./build_docker_image.sh

run_image:
	docker run -p 4545:4545 em-assignment-testing
