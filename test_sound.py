import pygame
import time

pygame.mixer.init()

sound = pygame.mixer.Sound(r"C:\Windows\Media\Windows Notify System Generic.wav")
sound.set_volume(1.0)

print("Playing test sound...")
sound.play()

time.sleep(2)