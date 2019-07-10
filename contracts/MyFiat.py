# 在外部Fiat不可用时使用自己的合约替代

# 定义一个价格变化事件
SetEthPrice: event({_from: uint256, _to: uint256})
RequestUpdate: event({_id: uint256})
Donation: event({_from: address})

# 定义状态变量
price: public(uint256)

setter: public(address)


@public
def __init__():
    self.setter = msg.sender


@public
@payable
def requestUpdate(id: uint256):
    """
    @dev public function for requesting an updated price from server
         using this function requires a payment of $0.35 USD
    @param id=0
    """
    need: wei_value = as_wei_value(self.price, 'wei') * 35
    assert msg.value >= need
    send(self.setter, msg.value)
    log.RequestUpdate(0)


@public
def setPrice(_price: uint256):
    assert msg.sender == self.setter
    log.SetEthPrice(self.price, _price)
    self.price = _price


@public
@constant
def USD(id: uint256) -> uint256:
    """
    @returns $0.01 worth of ETH in USD.
    """
    assert id == 0
    return self.price


@public
@payable
def donate():
    """
    @dev donation function that get forwarded to the contract setter
    """
    assert msg.value > 0
    send(self.setter, msg.value)
    log.Donation(msg.sender)
