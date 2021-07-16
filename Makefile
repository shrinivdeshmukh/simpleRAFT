install: 
	pip install -r requirements.txt

local:
	bash ./local_run.sh

logs:
	tail -F ./raft/.data/*.log

stop:
	bash ./local_stop.sh

docker: build
	docker-compose up -d

docker-logs:
	docker-compose logs -f

docker-stop:
	docker-compose down -v

build:
	docker-compose build