import _thread
import time

terminate = False

def my_thread():
  global terminate
  print("New thread is running...")
  while not terminate:
    time.sleep(0.2) 
  print("New thread is terminating gracefully.")
    
_thread.start_new_thread(my_thread, ())

try:
  while True:
    time.sleep(2) 
except KeyboardInterrupt:
  terminate = True
  time.sleep(0.3)
  print("Main thread terminated gracefully.")
