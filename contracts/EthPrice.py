#本合约用来获得ETH对USD的价格,返回的是0.01$对应的WEI数量
#使用以太坊上现存的Fiat Contract，官方网站为https://fiatcontract.com/
#其在主网和测试网上的地址为
#price = FiatContract(0x8055d0504666e2B6942BeB8D6014c964658Ca591) // MAINNET ADDRESS
#price = FiatContract(0x2CDe56E5c8235D6360CCbb0c57Ce248Ca9C80909) // TESTNET ADDRESS (ROPSTEN)

#定义外部合约接口
contract FiatContract:
    def USD(_id: uint256) -> uint256: constant
    def requestUpdate(_id: uint256):modifying


#定义状态变量
fiator:public(FiatContract)
owner:public(address)

@public
def __init__():
    self.owner = msg.sender

#允许切换到自己的备份合约
@public
def setFiator(_faitor:address):
    assert msg.sender == self.owner and _faitor !=ZERO_ADDRESS
    self.fiator = FiatContract(_faitor)

# @returns $0.01  => wei 假设返回值是 x ,对应的eth 就是 msg.value/return
@public
@constant
def getEthPrice() -> uint256:
    return self.fiator.USD(0)


@public
@payable
def updateEthPrice() -> bool:
    self.fiator.requestUpdate(0,value=msg.value)
    return True
