First we need to start pocketbase inside the backend/pocketbase folder with the command:
./pocketbase serve

Then we start the python server that handles the communication with the llm. it is inside the backend/server folder. We activate the venv first with:
 .\venv\Scripts\Activate  

 and then run the brain aka server with:
 python brain.py
 oder mittlerweile
 python main.py

 next we start the frontend inside the frontend folder with 
 npm run dev

 