import os
import threading
import pygame

class NotificationManager:
    def __init__(self, sound_file, volume_var):
        self.sound_file = sound_file
        self.volume_var = volume_var

    def play_notification(self):
        file_to_play = self.sound_file.get()

        if not os.path.exists(file_to_play):
            print(f"Selected file '{file_to_play}' not found, using 'default.wav'")
            file_to_play = "default.wav"

        if not os.path.exists(file_to_play):
            print("Error: Notification sound file not found! No sound will play.")
            return  

        print(f"Playing notification sound: {file_to_play} at volume: {self.volume_var.get()}")

        def play_sound():
            try:
                pygame.mixer.init()
                sound = pygame.mixer.Sound(file_to_play)
                sound.set_volume(self.volume_var.get())  
                sound.play()
            except pygame.error as e:
                print(f"Error loading sound file: {e}")

        threading.Thread(target=play_sound, daemon=True).start()