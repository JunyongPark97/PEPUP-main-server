### 초기 local 세팅
pip install -r requirements.txt
cd pepup
python manage.py makemigrations
python manage.py migrate
source .bash_profile_dev
python manage.py runserver

### 그 후
python manage.py runserver