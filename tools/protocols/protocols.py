from enum import Enum

class Protocols(Enum):
  HS304 = 'hs304'
  AmazonBasics = 'amazon'
  Canon = 'canon'
  def __str__(self):
    return self.value