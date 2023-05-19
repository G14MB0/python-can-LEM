import can
import can.interfaces.vector
import cantools
import matplotlib.pyplot as plt
import time
import threading
import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import tkinter.scrolledtext as stext

# Create the pause condition.
pause_condition = threading.Condition()
pause_flag = False


# Set up the CAN bus
bus = can.interface.Bus(bustype='vector', app_name='LEM', channel=0, bitrate=500000)


timestamps = []  # List to store timestamps
current_values = []  # List to store current values
file_duration = 24 * 60 * 60  # File duration in seconds (24 hours)
start_time = time.time()
file_counter = 1
file_name = f"LEM_Sensor_{file_counter}.txt"

# Load the DBC file
db = cantools.database.load_file('LEM.dbc')

# Set up a listener to read all incoming messages
def print_message(msg, file):
    global timestamps, current_values
    decoded_msg = db.decode_message(msg.arbitration_id, msg.data)
    # print(decoded_msg, end="\r")
    decoded_msg['timestamp'] = time.time()
    line = str(decoded_msg) + "\n"
    file.write(line)
    file.flush()
    # Update the text area with the latest message
    text_area.insert(tk.END, line)
    text_area.see(tk.END)  # automatically scroll to the end


listener = can.BufferedReader()
notifier = can.Notifier(bus, [listener])



def worker():
    global file_name, start_time, file_duration, running, pause_condition, root, save_directory

    # # Let the user select the saving path
    save_directory = select_directory()
    # Check if a directory was selected
    if not save_directory:
        messagebox.showwarning("Warning", "No directory selected. Exiting.")
        running = False
        root.destroy()
        return
    
     # Ensure the file path is correct
    file_name = save_directory + "/" + file_name

    # Create the first file
    with open(file_name, 'w') as file:
        # Start reading messages
        while running:
             # If paused, wait until the event is cleared
            with pause_condition:
            # If paused, wait until notified
                while pause_flag:
                    pause_condition.wait()
            try:
                # time.sleep(0.1)
                msg = listener.get_message(timeout=1)
                if msg is not None:
                    print_message(msg, file)
            except KeyboardInterrupt:
                break

            # Check if the current file duration exceeds 24 hours
            current_time = time.time()
            if current_time - start_time >= file_duration:
                # Close the current file
                file.close()
                # Increment the file counter and create a new file
                file_counter += 1
                file_name = f"name{file_counter}.txt"
                with open(file_name, 'w') as new_file:
                    file = new_file
                # Update the start time
                start_time = current_time

    # Clean up
    notifier.stop()
    bus.shutdown()


running = True


def on_closing():
    global running
    print("No directory selected. Exiting.")
    running = False
    root.destroy()



def pause_can_thread():
    global pause_condition, pause_flag
    with pause_condition:
        pause_flag = True

def play_can_thread():
    global pause_condition, pause_flag
    with pause_condition:
        pause_flag = False
        pause_condition.notify_all()


def stop_can_thread():
    global running, root
    if messagebox.askyesno("Confirm", "Are you sure you want to stop?"):
        running = False
        root.destroy()  # This will close the Tkinter window

def select_directory():
    # Show a message before asking for the directory
    messagebox.showinfo("Information", "Please select a directory for saving files")
    directory = filedialog.askdirectory()
    return directory
    # Check if a directory was selected




# Create the GUI
root = tk.Tk()
root.title("CAN Data Acquisition")
root.geometry("500x300")

# Create a scrollable text area
text_area = stext.ScrolledText(root)
text_area.grid(row=0, column=3, pady=10, padx=10)

# Create a pause button
pause_button = tk.Button(root, text="Pause", command=pause_can_thread)
pause_button.grid(row=0, column=0, pady=10, padx=10, sticky='w')

# Create a play button
play_button = tk.Button(root, text="Play", command=play_can_thread)
play_button.grid(row=0, column=1, pady=10, padx=10, sticky='w')

# Create a stop button
stop_button = tk.Button(root, text="Stop", command=stop_can_thread)
stop_button.grid(row=0, column=2, pady=10, padx=10, sticky='w')


# Start reading CAN messages in a separate thread
can_thread = threading.Thread(target=worker)
can_thread.start()

# Start the GUI event loop
root.mainloop()