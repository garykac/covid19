echo "Downloading US/Italy data for $1"

ITALY_URL=https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/dati-andamento-nazionale/dpc-covid19-ita-andamento-nazionale.csv
ITALY_FILE=data/dpc-covid19-ita-andamento-nazionale.csv

US_URL=https://covidtracking.com/api/v1/states/daily.csv
US_FILE=data/states-daily.csv

curl -o $ITALY_FILE $ITALY_URL
curl -o $US_FILE $US_URL

git commit -a -m "Snapshot US/Italy data for $1"

python plot.py --top
