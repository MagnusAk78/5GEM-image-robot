import math

class Face(): 
    def __init__(self, x, y, width, height): 
        self.x = x
        self.y = y
        self.w = width
        self.h = height
        
    def centerX(self):
        return self.x + self.w / 2
        
    def centerY(self):
        return self.y + self.h / 2        
        
    def distanceTo(self, otherFace):
        distX = abs(self.centerX() - otherFace.centerX())
        distY = abs(self.centerY() - otherFace.centerY())
        return math.sqrt(distX * distX + distY * distY)
    
    def size(self):
        return math.sqrt(self.w * self.w + self.h * self.h)

    def sizeDiff(self, otherFace):
        return abs(self.size() - otherFace.size())
        
NO_FACE = Face(-1,-1,-1,-1)
