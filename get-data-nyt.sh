echo "Downloading US/Italy data for $1 $2 $3"

NYT_URL=https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv
NYT_FILE=data/nyt/us-counties.csv

curl -o $NYT_FILE $NYT_URL

git commit -a -m "Snapshot NYT data for $1 $2 $3"

python map.py

git commit -a -m "Generate maps for $1 $2 $3"
