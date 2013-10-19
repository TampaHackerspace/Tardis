"""
This code is provided 'AS IS' and is intended to be an example of how a Python
game can be written, with the hope people will modify it, learn from it,
and improve it!

Anyone is free to copy, modify, use, compile, or distribute this software,
either in source code form or as a compiled binary, for any non-commercial
purpose.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

"""  


#NAM: Start Setup GPIO
import RPi.GPIO as GPIO
import time
import serial
ser = serial.Serial('/dev/ttyACM0')

WAIT_TIME = .3      # .3 seconds

#GREEN_LED = 18
RED_LED = 23
BUTTON1 = 24
BUTTON2 = 4
BUTTON3 = 18


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(BUTTON1, GPIO.IN)
GPIO.setup(BUTTON2, GPIO.IN)
GPIO.setup(BUTTON3, GPIO.IN)

#GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)

GPIO.add_event_detect(BUTTON1, GPIO.BOTH)  #NAM Add rising edge detection to Button2
GPIO.add_event_detect(BUTTON2, GPIO.BOTH)  #NAM Add rising edge detection to Button2
GPIO.add_event_detect(BUTTON3, GPIO.BOTH)  #NAM Add rising edge detection to Button3

#NAM: End Setup GPIO

import random
import pygame, sys
from pygame.locals import *
from pygame.surface import Surface
import math

screen_width_pixels = 800
screen_height_pixels = 600

pygame.init()
pygame.display.set_caption("Tardis Lander")
#NAM: kill fullscreen screen=pygame.display.set_mode((screen_width_pixels, screen_height_pixels), pygame.FULLSCREEN, 32)
screen=pygame.display.set_mode((screen_width_pixels, screen_height_pixels), 32)
pygame.mouse.set_visible(0)
screen.fill((255, 255, 255))
pygame.display.update()

background=pygame.image.load("Resources/background.png").convert()
background2=pygame.image.load("Resources/background2.png").convert()
titleImage = pygame.image.load("Resources/titleimage.jpg").convert()
uiFont = pygame.font.SysFont("monospace", 12)
uiFontBig = pygame.font.SysFont("monospace", 48)


background_image_height = Surface.get_height(background)
screenScroll = 0


def blitTextCentered(font, text, surface, color):
    """ Utility function for drawing text at the centre of a 'Surface'. """
    label = font.render(text, True, color)
    textRect = label.get_rect()
    textRect.center = surface.get_rect().center
    surface.blit(label, textRect)
    
def blitTextHorizontalCentered(font, text, y, leftX, width, surface, color):
    """ Utility function for drawing text at the horizontal centre of the screen. """
    label = font.render(text, True, color)
    textRect = label.get_rect()
    textRect.top = y
    textRect.center = (leftX + width / 2, textRect.center[1])
    surface.blit(label, textRect)

class TardisSprite(pygame.sprite.Sprite):
    """
    Store the position and animation frame for the Tardis.
    
    IDEA: Try changing the tardis*.png bitmaps, but we recommend you keep the images
    the same size as ours.
    """
    _animFrame = 0
    _isLanding = False
    _imageResample = 0.5

    def __init__(self, initialFuel):
        self._tardisFrame = []
        self._tardisFrame.append(pygame.image.load("Resources/tardis0.png").convert_alpha())
        self._tardisFrame.append(pygame.image.load("Resources/tardis1.png").convert_alpha())
        self._tardisFrame.append(pygame.image.load("Resources/tardis2.png").convert_alpha())
        self._tardisFrame.append(pygame.image.load("Resources/tardisLand0.png").convert_alpha())
        self._tardisFrame.append(pygame.image.load("Resources/tardisLand1.png").convert_alpha())
        self._tardisFrame.append(pygame.image.load("Resources/tardisLand2.png").convert_alpha())

        self.tardisHeight = Surface.get_height(self._tardisFrame[0]) * self._imageResample
        self.tardisWidth = Surface.get_width(self._tardisFrame[0]) * self._imageResample
        self.altitude = screen_height_pixels - self.tardisHeight * 1 #NAM: Adjust start height

        self._landingStickLength = max(self.tardisHeight, self.tardisWidth)

        self.x = 50
        self.angle = 0
        self.angleDelta = 0
        self.velocityX = 0.1
        self.velocityY = 0
        self.thrusting = False
        self.image = pygame.transform.rotozoom(self._tardisFrame[0], 0, self._imageResample)
        self.rotate(45)
        self.thrustSound = pygame.mixer.Sound('Resources/tardisthrust.ogg')
        self.thrustSound.set_volume(0.5)
        self.fuel = initialFuel

        pygame.sprite.Sprite.__init__(self)
        self.rect = Rect(self.x, 0, self.tardisWidth, self.tardisWidth)
        
        self.maxHeight = math.sqrt(self.tardisHeight * self.tardisHeight + self.tardisWidth * self.tardisWidth)
        self.rotationsPerSec = 0.2
        
        self.recalculateRect()

    def getAngle(self):
        angle = self.angle
        while angle < -180:
            angle += 360
        while angle > 180:
            angle -= 360

        return -angle

    def getSpeed(self):
        return math.sqrt(self.velocityX * self.velocityX + self.velocityY * self.velocityY)

    def rotate(self, angleDelta):
        self.angle -= angleDelta

        if self._isLanding:
            frame = 3 + (self._animFrame if self.thrusting else 0)
        else:
            frame = self._animFrame

        originalRect = self.image.get_rect().copy()
        self.image = pygame.transform.rotozoom(self._tardisFrame[frame], self.angle, self._imageResample)
        originalRect.center = self.image.get_rect().center
        self.image = self.image.subsurface(originalRect).copy()
        
        self.mask = pygame.mask.from_surface(self.image)

    def height(self):
        return self.tardisHeight

    def width(self):
        return self.tardisWidth

    def thrust(self, thrusting):
        if thrusting and self.fuel == 0:
            thrusting = False

        if self.thrusting == thrusting:
            return

        self.thrusting = thrusting
        if thrusting:
            self.thrustSound.play(-1)
        else:
            self.thrustSound.fadeout(500)
            self.setAnimFrame(0)

    def updateThrustAnim(self):
        assert self.thrusting
        if math.fmod(pygame.time.get_ticks(), 200) > 100:
            self.setAnimFrame(1)
        else:
            self.setAnimFrame(2)

    def setAnimFrame(self, frameNumber):
        if self._animFrame <> frameNumber:
            self._animFrame = frameNumber
            self.rotate(0)
            
    def recalculateRect(self):
        global screenScroll

        screenTopScrollMargin = 40
        screenBottomScrollMargin = screen_height_pixels - 250

        if self.velocityY > 0 and self.altitude > background_image_height - self.maxHeight:
            self.velocityY = 0

        cy = background_image_height - self.altitude + screenScroll

        if cy < screenTopScrollMargin and self.velocityY > 0:
            screenScroll += screenTopScrollMargin - cy
            cy = background_image_height - self.altitude + screenScroll
        elif cy > screenBottomScrollMargin and self.velocityY < 0:
            screenScroll = max(screenScroll + screenBottomScrollMargin - cy, screen_height_pixels - background_image_height)
            cy = background_image_height - self.altitude + screenScroll

        self.rect.center = (self.x, cy)

    def landingStickEnd(self):
        angleRads = self.angle * math.pi / 180.0
        landingStickX = self.x + math.sin(angleRads) * self._landingStickLength
        landingStickY = self.rect.center[1] + math.cos(angleRads) * self._landingStickLength
        return landingStickX, landingStickY

    def prepareForLanding(self, isLanding):
        if self._isLanding == isLanding:
            return
        self._isLanding = isLanding
        self.rotate(0)


class PhysicsEngine():
    """
    Apply the effects of physics to the Tardis.
    
    IDEA: Want to change how much gravity there is? See self.gravityAcceleration.
    """
    def __init__(self, Tardis):
        tardis_height_metres = 1.0
        pixels_per_metre = Tardis.height() * tardis_height_metres

        self.gravityAcceleration = -0.04
        self.thrustAcceleration = 0.2
        self._Tardis = Tardis
        self._pixels_per_metre = pixels_per_metre

    def tick(self, deltaSecs):
        self._applyGravity(deltaSecs)

        if self._Tardis.thrusting:
            if self._Tardis.fuel > 0:
                self._applyThrust(deltaSecs)
            else:
                self._Tardis.thrust(False)
        else:
            self._Tardis.velocityX *= 0.999 # Apply a small amount of 'drag force' to the Tardis.

        deltaY = self._Tardis.velocityY * deltaSecs
        self._Tardis.altitude += deltaY * self._pixels_per_metre

        self._Tardis.deltaX = self._Tardis.velocityX * deltaSecs
        self._Tardis.x += self._Tardis.deltaX * self._pixels_per_metre

    def _applyGravity(self, deltaSecs):
        """
        Gravity always acts on the Tardis.
        
        IDEA: ...or does it?? Comment out this code, or change self.gravityAcceleration
        to 0 to change how the game plays!
        """
        self._Tardis.velocityY += self.gravityAcceleration * deltaSecs

    def _applyThrust(self, deltaSecs):
        """ Update the state of the Tardis when his thrust is active. """
        angleRads = self._Tardis.angle * math.pi / 180.0
        distanceMoved = self.thrustAcceleration * deltaSecs * thrustMultiplier  #NAM Add thrustMultiplier to fake analog input

        self._Tardis.thrustY = math.cos(angleRads)
        self._Tardis.velocityY += distanceMoved * self._Tardis.thrustY

        self._Tardis.thrustX = -math.sin(angleRads)
        self._Tardis.velocityX += distanceMoved * self._Tardis.thrustX

        self._Tardis.fuel = max(0, self._Tardis.fuel - deltaSecs * 250)
        self._Tardis.updateThrustAnim()


class LunarSurface(pygame.sprite.Sprite):
    image = None
    _groundElevation = 20
    _flatWidth = 70
    _easyFlatWidth = 100

    def __init__(self):
        self.groundSurface = 0
        self._createSurface()

        pygame.sprite.Sprite.__init__(self)
        self.rect = self.image.get_rect()
        self.rect.topleft = (0, 0)
        self.mask = pygame.mask.from_surface(self.image)

    def _createSurfacePoints(self):
        """
        Generate the surface terrain, making sure the correct number of 'flats'
        are added.
        """
        numberofFlats = 0
        numberofEasyFlats = 0
        justMadeFlat = False
        #NAM while numberofFlats != 3 or numberofEasyFlats != 2: # Change these values for more/less 'flats'.
        while numberofFlats != 0 or numberofEasyFlats != 3: #NAM Make them ALL "EasyFlats".
            numberofFlats = 0
            numberofEasyFlats = 0
            max_surface_height = screen_height_pixels / 4.0
            self._drop_amount = 0
            self._pointsX = []
            self._pointsY = []
            self._flatCoordinates = []
            self._flatEasyCoordinates = []
            
            # Add first point.
            x = 0
            self._pointsX.append(x)
            y = max_surface_height / 2.0
            self._pointsY.append(y)
            
            # Create surface until we get to the end of the screen.
            while x < screen_width_pixels:
                deltaY = random.randint(-40, 40)
                while y + deltaY >= max_surface_height or y + deltaY < 0 or deltaY == 0:
                    deltaY = random.randint(-40, 40)
                
                y += deltaY
                self._pointsY.append(deltaY)
                rand = random.randint(0, 100)
                if rand > 85 and x < (screen_width_pixels - self._flatWidth) and x > 0 and not justMadeFlat:
                    justMadeFlat = True
                    numberofFlats += 1
                    x = min(x + self._flatWidth, screen_width_pixels)
                    self._pointsX.append(x)
                    self._pointsY[len(self._pointsY) - 1] = 0
                    self._flatCoordinates.append(len(self._pointsX) - 2)
                elif rand > 70 and rand < 84 and x < (screen_width_pixels - self._flatWidth) and x > 0 and not justMadeFlat:
                    justMadeFlat = True
                    numberofEasyFlats += 1
                    x = min(x + self._easyFlatWidth, screen_width_pixels)
                    self._pointsX.append(x)
                    self._pointsY[len(self._pointsY) - 1] = 0
                    self._flatEasyCoordinates.append(len(self._pointsX) - 2)
                else:
                    justMadeFlat = False
                    x = min(x + random.randint(10, 40), screen_width_pixels)
                    self._pointsX.append(x)
            
            # 'Drop' the surface so it always appears near the bottom of the screen.
            currentY = lowestSurfacePoint = self._pointsY[0]
            highestY = currentY
            for i in range(1, len(self._pointsX) - 1):
                currentY += self._pointsY[i]
                lowestSurfacePoint = min(lowestSurfacePoint, currentY)
                highestY = max(highestY, currentY)
            
            self._drop_amount = lowestSurfacePoint
        return highestY - lowestSurfacePoint
    
    def _plotlandingScores(self, surfaceCoords):
        """ Draw the score values just under each 'flat'. """
        for i in range(0, len(self._flatCoordinates)):
            surfaceIndex = self._flatCoordinates[i]
            surfaceCoord = self._pointsX[surfaceIndex], surfaceCoords[surfaceIndex][1] + 4
            blitTextHorizontalCentered(uiFont, "x10", surfaceCoord[1], surfaceCoord[0], self._flatWidth, LunarSurface.image, (255, 255, 0))
        for i in range(0, len(self._flatEasyCoordinates)):
            surfaceIndex = self._flatEasyCoordinates[i]
            surfaceCoord = self._pointsX[surfaceIndex], surfaceCoords[surfaceIndex][1] + 4
            #blitTextHorizontalCentered(uiFont, "x5" + str(surfaceCoord[0]) + " " + str(surfaceCoord[1]), surfaceCoord[1], surfaceCoord[0], self._easyFlatWidth, LunarSurface.image, (255, 255, 0))
            
            #NAM Get Locations For RadioShacks (Ugly Hack Assumes 3 RShacks)
            global RShackImage, RShack1X, RShack1Y, RShack2X, RShack2Y, RShack3X, RShack3Y 
            RShackImage = pygame.image.load("Resources/radio-shack-1.png").convert_alpha()
            
            #NAM Count the loop and update the RShack Locations
            if  i == 0:
                RShack1X = surfaceCoord[0]
                RShack1Y = 600-76 #NAM Can't figure out Y... surfaceCoord[0]

            if  i == 1:
                RShack2X = surfaceCoord[0]
                RShack2Y = 600-76
            
            if  i == 2:
                RShack3X = surfaceCoord[0]
                RShack3Y = 600-76

            
    def _createSurfaceImage(self, surfaceHeight):
        """
        Make the ground surface image.
        
        IDEA: Try changing the color of the ground, or maybe even add a texture to it.
        """
        LunarSurface.image = pygame.Surface([screen_width_pixels, surfaceHeight + self._groundElevation], pygame.SRCALPHA, 32).convert_alpha()
        initialY = y = Surface.get_height(LunarSurface.image) - self._pointsY[0] + self._drop_amount - self._groundElevation
        polyCoords = [(0, y)]

        for i in range(1, len(self._pointsX)):
            y -= self._pointsY[i]
            polyCoords.append((self._pointsX[i], y))
        
        surfaceCoords = list(polyCoords)
        polyCoords.append([screen_width_pixels, Surface.get_height(LunarSurface.image)])
        polyCoords.append([0, Surface.get_height(LunarSurface.image)])
        polyCoords.append([0, initialY])
        pygame.draw.polygon(LunarSurface.image, (64, 64, 64,128), polyCoords, 0)
        for i in range(0, len(surfaceCoords) - 1):
            if self._flatCoordinates.count(i) or self._flatEasyCoordinates.count(i):
                #NAM change color: color = 0, 255, 255
                color = 255, 0, 0
                width = 3
            else:
                color = 128, 128, 128
                width = 1
            pygame.draw.line(LunarSurface.image, color, surfaceCoords[i], surfaceCoords[i + 1], width)

        self._plotlandingScores(surfaceCoords)

    def _createSurface(self):
        surfaceHeight = self._createSurfacePoints()
        self._createSurfaceImage(surfaceHeight)

    
    def _isPointOnFlat(self, x):
        """
        Returns True and the value of the 'flat' being landed on, or
        False and 0 if the 'flat' has been missed.
        """
        for i in range(0, len(self._flatCoordinates)):
            index = self._flatCoordinates[i]
            if self._pointsX[index] <= x and x <= self._pointsX[index + 1]: 
                return True, 10
        for i in range(0, len(self._flatEasyCoordinates)):
            index = self._flatEasyCoordinates[i]
            if self._pointsX[index] <= x and x <= self._pointsX[index + 1]: 
                return True, 5
        
        return False, 0
    
    
    def isTardisOnFlat(self, Tardis):
        legsApart = 16
        tardisCenterX = Tardis.rect.left + Tardis.rect.width / 2
        leftFoot = tardisCenterX - legsApart / 2
        rightFoot = tardisCenterX + legsApart / 2
        
        leftFootInfo = self._isPointOnFlat(leftFoot)
        rightFootInfo = self._isPointOnFlat(rightFoot)
        
        if leftFootInfo[0] and rightFootInfo[0]: 
            return leftFootInfo
        return False, 0


def show_fuel(Tardis):
    """ Draw the fuel in the top-left corner of the screen. """
    label = uiFont.render(" Fuel: " + str(int(Tardis.fuel)), True, (255, 255, 0))
    screen.blit(label, (10, 10))


def show_angle(Tardis):
    """ Draw the angle in the top-left corner of the screen. """
    label = uiFont.render("Angle: " + str(int(Tardis.getAngle())), True, (255, 255, 0))
    screen.blit(label, (10, 25))

def show_speed(Tardis):
    """ Draw the speed in the top-left corner of the screen. """
    label = uiFont.render("Speed: " + str(int(Tardis.getSpeed() * 100)), True, (255, 255, 0))
    screen.blit(label, (10, 40))


def show_score(gameStats):
    """ Draw the score in the top-left corner of the screen. """
    label = uiFont.render("Score: " + str(gameStats.displayScore), True, (255, 255, 0))
    screen.blit(label, (10, 55))


def show_multiplier(Tardis):
    #NAM Display the current multiplier
    label = uiFontBig.render("Power: " + str(thrustMultiplier), True, (255, 255, 0))
    screen.blit(label, (500, 30))
	
	
def quitGame():
    """ Shut down the game """
    pygame.quit()
    sys.exit()


def tardisDeath():
    """ This is called when the Tardis has crashed. """
    GPIO.output(RED_LED, False)     #NAM Reset GPIO OUTPUTs
    #GPIO.output(GREEN_LED, False)   #NAM Reset GPIO OUTPUTs

    pygame.mixer.music.load('Resources/gameover.ogg')
    pygame.mixer.music.play()
    sadTardis = pygame.image.load("Resources/gameover.png").convert_alpha()
    pygame.mixer.fadeout(2000)
    screen.blit(sadTardis,((screen_width_pixels - 300) / 2, (screen_height_pixels - 200) / 2))
    pygame.display.update()
    pygame.time.wait(4000)


def tardisLanded(Tardis, flatScore, lunarSurface, gameStats):
    """
    This is called when the Tardis has made a safe landing.
    The score is added up as the fuel is counted down.
    
    IDEA: You may want to take into account how long it took the Tardis
    to land.  A quicker time could mean more score!
    """
    levelScore = int(Tardis.fuel * flatScore)
    gameStats.totalScore += levelScore
    font = pygame.font.Font("Resources/gothic.ttf", 45)

    pygame.mixer.music.load('Resources/beep.ogg')
    pygame.mixer.music.set_volume(0.5)

    fuelRemaining = int(Tardis.fuel) + 1
    while fuelRemaining > 0:
        fuelStep = min(33, fuelRemaining)
        if fuelStep == 33:
            pygame.mixer.music.play()
        else:
            pygame.mixer.music.stop()

        fuelRemaining -= fuelStep
        gameStats.displayScore += fuelStep

        redrawScreen(Tardis, lunarSurface)
        show_stats(Tardis)

        show_score(gameStats)
        blitTextHorizontalCentered(font, 'Level Cleared', 225, 365, 50, screen, (255,255,0))
        label = font.render("Remaining Fuel: " + str(fuelRemaining), True, (255, 255, 0))
        screen.blit(label, (230, 280))

        pygame.display.update()
        pygame.time.wait(75)
        
    pygame.time.wait(3000)


def show_splashscreen():
    """
    Show the splash screen.
    This is called once when the game is first started.
    """
    pygame.mixer.music.load('Resources/splash.ogg')
    pygame.mixer.music.play()
    
    # Slowly fade the splash screen image from white to opaque. 
    splash = pygame.image.load("Resources/splash.png").convert()
    for i in range(25):
        splash.set_alpha(i)
        screen.blit(splash, (0,0))
        pygame.display.update()
        pygame.time.wait(100)

    pygame.mixer.fadeout(2000)
    screen.blit(splash,(0,0))
    pygame.display.update()
    pygame.time.wait(1500)


def show_titlescreen():
    """ 
    Show the main title screen, and wait for the user to press <SPACE>.
    If the user presses the 'ESCape' key we will quit the game.
    
    IDEA: You could add a difficulty selection option here. Perhaps
    detect if the user pressed 'E', 'M', or 'H' for Easy/Medium/Hard?
    
    IDEA: For the more adventurous you could even allow the user to
    start a two player game!
    """
    
    time.sleep(WAIT_TIME)
    
    global titleImage

    titleMusic = pygame.mixer.Sound('Resources/titlemusic.ogg')
    titleMusic.set_volume(.5)
    titleMusic.play(-1)
    titleFont = pygame.font.Font("Resources/matt_smith_doctor_who.ttf", 72)

    label = titleFont.render("PRESS A BUTTON", True, (255, 255, 255)) # BLUE: 167, 192, 216
    textRect = label.get_rect()
    textRect.center = (screen_width_pixels - 230, 125)

    while True:
        # Make the 'PRESS SPACE' text flash.
        screen.blit(titleImage, (0,0))
        if math.fmod(pygame.time.get_ticks(),1000) > 500:
            screen.blit(label, textRect)

        for event in pygame.event.get():
            if event.type == QUIT:
                quitGame()
            if event.type==KEYDOWN:
                if event.key==K_SPACE:
                    titleMusic.fadeout(500)
                    return
                elif event.key==K_ESCAPE:
                    quitGame()
        if GPIO.event_detected(BUTTON1) or GPIO.event_detected(BUTTON2) or GPIO.event_detected(BUTTON3): #NAM START WITH GPIO Button
            titleMusic.fadeout(500)
            return
        pygame.display.update()


currentMusic = ""
def playMusic(name):
    """ Load and play the music file specified by 'name'. """
    global currentMusic
    
    if currentMusic == name:
        return
    currentMusic = name

    pygame.mixer.music.load("Resources/" + name)
    pygame.mixer.music.play(-1)


def checkForLandingPosition(Tardis, lunarSurface):
    """
    Check to see if the area below the Tardis is the ground.
    If it is, then we can put the Tardis into the 'landing position' and play
    the 'landing music'.
    """ 
    checkY = int(Tardis.landingStickEnd()[1] - lunarSurface.rect.top)
    isLanding = False

    if checkY >= lunarSurface.rect.height - 100:
        isLanding = True
    elif checkY >= 0:
        checkX = int(min(screen_width_pixels - 1, max(Tardis.landingStickEnd()[0], 0)))
        surfaceColorAtLandingStickEnd = lunarSurface.image.get_at((checkX, checkY))
        if (surfaceColorAtLandingStickEnd[3] != 0):
            isLanding = True
            
    Tardis.prepareForLanding(isLanding)
    if isLanding:
        playMusic("landing.ogg")
        #NAM write to serial for landing.
        ser.write('3')
    else:        
        playMusic("bgmusic.ogg")
        #NAM write to serial for landing.
        ser.write('2')
        

def redrawScreen(Tardis, lunarSurface):
    """
    Draw the 'space' background, the ground, and the Tardis.
    This is called several times a second to keep the screen updated.
    """
    global screenScroll

    #NAM: Randomly use a different background
    RandomBGLoopCount = random.randrange(1,10)
    RandomBGCount = random.randrange(1,10)
    CurrentBackground = background

    if RandomBGLoopCount == 3:
        if RandomBGCount%2==0:
            CurrentBackground = background
        else:
            CurrentBackground = background2

    screen.blit(CurrentBackground, (0, 0), (0, -screenScroll, screen_width_pixels, screen_height_pixels))

    #screen.blit(background2, (0, 0), (0, -screenScroll, screen_width_pixels, screen_height_pixels))
    #screen.blit(background, (0, 0), (0, -screenScroll, screen_width_pixels, screen_height_pixels)) 

    #NAM Redraw the RadioShacks
    screen.blit(RShackImage, (RShack1X,RShack1Y))
    screen.blit(RShackImage, (RShack2X,RShack2Y))
    screen.blit(RShackImage, (RShack3X,RShack3Y))

    screen.blit(lunarSurface.image, lunarSurface.rect)
    screen.blit(Tardis.image, Tardis.rect)
   
    bgloopcount = 0
    bgloopcount = bgloopcount + 1
   
def show_stats(Tardis):
    """
    Update the score/angle/fuel counters shows at the top-left corner of
    the screen.
    """
    show_angle(Tardis)
    show_fuel(Tardis)
    show_speed(Tardis)
    show_multiplier(Tardis)

def tardisGameLoop(gameStats):
    global screenScroll

    playMusic("bgmusic.ogg")

    #NAM write to serial for landing.
    ser.write('1')
    
    Tardis = TardisSprite(gameStats.initialFuel)
    physicsEngine = PhysicsEngine(Tardis)
    lunarSurface = LunarSurface()

    """ IDEA: Change these values to change how easy it is to land the Tardis. """
    maxLandingVelocity = -0.20
    maxLandingAngle = 7

    screenScroll = screen_height_pixels - background_image_height

    clock = pygame.time.Clock()
    
    UsingButtons = 0 #NAM Used to zero-out the button input and keep KB input working
    
    global thrustMultiplier #NAM Define standard thrustMultiplier (Used to fake analog thrust1) 
    thrustMultiplier = 1

    while True:
        time_elapsed_secs = clock.tick(50) / 1000.0
        """
        Checks to see if a key is pressed. If so, act accordingly.

        IDEA: If you wanted to add joystick support, you could
        do it here.
        """

        #NAM Read Serial
        if ser.inWaiting() > 0:
            #thrustMultiplier = int(float(ser.readline()[0]))
            SerialLastLine = ser.readline()
            if len(SerialLastLine) == 3:
                thrustMultiplier = int(float(SerialLastLine[0]))
            elif len(SerialLastLine) == 4:
                thrustMultiplier = int(float(SerialLastLine[0:2]))
            else:
                thrustMultiplier = int(float(SerialLastLine[0]))
                thrustMultiplier = len(SerialLastLine)
                

        if  UsingButtons == 1: #NAM Account for Button up.
            Tardis.angleDelta = 0
            Tardis.thrust(0)
            UsingButtons = 0
        
        if GPIO.input(BUTTON1):
            Tardis.angleDelta = -1
            UsingButtons = 1

        if GPIO.input(BUTTON2):
            Tardis.angleDelta = 1
            UsingButtons = 1

        if GPIO.input(BUTTON3):
            UsingButtons = 1            
            Tardis.thrust(1)
            #thrustMultiplier = 1

            
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type==KEYDOWN:
                if event.key==K_LEFT:
                    Tardis.angleDelta=-1
                elif event.key==K_RIGHT:
                    Tardis.angleDelta=1
                elif event.key==K_SPACE:
                    Tardis.thrust(1)
                    #global thrustMultiplier
                    thrustMultiplier = 1
                    GPIO.output(RED_LED, True) #NAM START GPIO OUTPUT for thrust

                elif event.key==K_1: #NAM Detect Variable Thrust level
                    Tardis.thrust(1)
                    #global thrustMultiplier
                    thrustMultiplier = 1
                    GPIO.output(RED_LED, True) #NAM START GPIO OUTPUT for thrust
                elif event.key==K_2: #NAM Detect Variable Thrust level
                    Tardis.thrust(1)
                    #global thrustMultiplier
                    thrustMultiplier = 2
                    GPIO.output(RED_LED, True) #NAM START GPIO OUTPUT for thrust
                elif event.key==K_3: #NAM Detect Variable Thrust level
                    Tardis.thrust(1)
                    #global thrustMultiplier
                    thrustMultiplier = 4
                    GPIO.output(RED_LED, True) #NAM START GPIO OUTPUT for thrust
                elif event.key==K_4: #NAM Detect Variable Thrust level
                    Tardis.thrust(1)
                    #global thrustMultiplier
                    thrustMultiplier = 8
                    GPIO.output(RED_LED, True) #NAM START GPIO OUTPUT for thrust
                elif event.key==K_5: #NAM Detect Variable Thrust level
                    Tardis.thrust(1)
                    #global thrustMultiplier
                    thrustMultiplier = 16
                    GPIO.output(RED_LED, True) #NAM START GPIO OUTPUT for thrust

                elif event.key==K_ESCAPE:
                    pygame.mixer.music.stop()
                    return False
            if event.type==KEYUP:
                if event.key==K_LEFT or event.key==K_RIGHT:
                    Tardis.angleDelta=0
                elif event.key==K_SPACE:
                    Tardis.thrust(0)
                    GPIO.output(RED_LED, False) #NAM End GPIO OUTPUT for thrust
                #NAM Detect Variable Thrust level
                elif event.key==K_1 or event.key==K_2 or event.key==K_3 or event.key==K_4 or event.key==K_5:
                    Tardis.thrust(0)
                    GPIO.output(RED_LED, False) #NAM End GPIO OUTPUT for thrust
                    
        # Apply the effect of thrust and gravity to the Tardis.
        physicsEngine.tick(time_elapsed_secs)

        # Bounce the Tardis horizontally off the screen.
        if Tardis.x < Tardis.width() / 2 and Tardis.velocityX < 0:
            Tardis.x = Tardis.width() / 2
            Tardis.velocityX *= -1
        elif Tardis.x > screen_width_pixels - Tardis.width() / 2 and Tardis.velocityX > 0:
            Tardis.x = screen_width_pixels - Tardis.width() / 2
            Tardis.velocityX *= -1

        # Spin the Tardis if needed.
        if Tardis.angleDelta <> 0:
            Tardis.rotate(Tardis.angleDelta * 360 * time_elapsed_secs * Tardis.rotationsPerSec)

        # Redraw the screen.
        lunarSurface.rect.topleft = (0, background_image_height - lunarSurface.rect.height + screenScroll)
        redrawScreen(Tardis, lunarSurface)

        # If the Tardis is near the ground, start 'landing mode'.
        Tardis.recalculateRect()
        checkForLandingPosition(Tardis, lunarSurface)

        show_stats(Tardis)
        show_score(gameStats)
        
        pygame.display.update()

        # Check to see if the Tardis is touching the ground.
        if pygame.sprite.collide_mask(Tardis, lunarSurface):
            Tardis.thrust(0)
            pygame.mixer.music.stop()

            if math.fabs(Tardis.getAngle()) <= maxLandingAngle and Tardis.velocityY >= maxLandingVelocity:
                # the Tardis has landed safely!
                scoreInfo = lunarSurface.isTardisOnFlat(Tardis)
                if scoreInfo[0]:
                    tardisLanded(Tardis, scoreInfo[1], lunarSurface, gameStats)
                    return True # 'True' will make the next level start.

            # the Tardis crashed!
            tardisDeath()

            #NAM write to serial for landing.
            ser.write('4')

            return False # 'False' will make the game go back to the title screen.


class GameStats:
    """
    Stores information about the Tardis's fuel and score.
    
    IDEA: You could add a self.highScore field to keep track the the game's
    highest score. Perhaps even write it to a file to score the highest ever score?
    """ 
    def __init__(self):
        self.displayScore = 0
        self.totalScore = 0
        self.initialFuel = 3000
        self.fuelReduction = 250

    def reduceFuel(self):
        """
        Reduces the amount of fuel to use at the beginning of each level.
    
        IDEA: Try changing the starting values of self.initialFuel and self.fuelReduction
        to change the difficulty of the game.  Maybe base these values on a Easy/Medium/Hard
        difficulty level? 
        """
        self.initialFuel = max(1000, self.initialFuel - self.fuelReduction)
    

def playLoop():
    """
    This will keep playing the a level at a time, until tardisGameLoop() tells
    us to stop. (Such as if the Tardis crashes.)
    """
    gameStats = GameStats()
    playAgain = True
    while playAgain:
        playAgain = tardisGameLoop(gameStats)
        gameStats.reduceFuel()


""" This is where the game starts. """
show_splashscreen()
while True:
    show_titlescreen()
    playLoop()
