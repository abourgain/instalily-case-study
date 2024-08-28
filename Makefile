# Installer toutes les dépendances du projet
install:
	cd ./frontend; npm install
	conda env create -f ./backend/environment.yml

# Start frontend
front:
	cd ./frontend; npm start

### ---------------   Lint  --------------- ###

eslint:
	cd ./frontend; npm run lint

pylint:
	pylint --rcfile=./backend/pylint.conf backend

lint:
	make eslint
	make pylint

### ---------------   Format  --------------- ###

black:
	black ./backend

format: 
	make black