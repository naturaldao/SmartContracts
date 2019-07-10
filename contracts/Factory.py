# @dev Implementation of control contract
# @author radarzhhua@gmail.com
from vyper.interfaces import ERC20


# the contract of NDAO ERC20 token
contract NDAO:
    def mint(_to: address, _value: uint256): modifying
    def decimals() -> uint256: constant


# the exchange contract
contract Exchange:
    def setup(token_addr: address, ndao_address: address,
              token_amount: uint256): modifying


# the ICO contract
contract ICO:
    def setup(_name: string[64], _symbol: string[32], _decimals: uint256, _depositGoal: uint256,
              _deltaOfEnd: timedelta, _deltaOfSubmitssion: timedelta, token_price: uint256, _creater: address): modifying


# ETH价格查询合约
contract QueryEthPrice:
    def getEthPrice() -> uint256: constant


# no enum
STATUS_NONE: constant(uint256) = 0  # 0
STATUS_STARTED: constant(uint256) = 1  # 1
STATUS_SUCCESS: constant(uint256) = 2  # 2
STATUS_FAILED: constant(uint256) = 3  # 3
MAX_NUMBER: constant(int128) = 128

# 定义对应事件
NewExchange: event(
    {_token: indexed(address), _exchange: indexed(address), _amount: uint256, _tokenAmount: uint256})
ICOCreated: event({_creater: indexed(address), _ico: address})
ICOUpdate: event({_token: indexed(address), _status: uint256})
NewSetter: event({_from: indexed(address), _to: indexed(address)})
NewSubmitDelta: event({_newDelta: timedelta})

exchangeTemplate: public(address)  # 交易模板里面含有代码，可以创建新合约，方法为Exchange的setup方法
icoTemplate: public(address)  # ICO模板
tokenCount: public(uint256)  # token编号
token_to_exchange: public(map(address, address))  # token地址 =>根据模板创建的合约地址
exchange_to_token: public(map(address, address))  # token对应的合约地址 => token地址
id_to_token: public(map(uint256, address))  # token编号 => 地址
beneficiary: public(address)  # 保存锻造ETH的地址
ndaoAddress: public(address)  # 稳定币地址
queryAddress: public(address)  # ETH价格查询合约地址
allIcoStatus: public(map(address, uint256))  # 所有通过本合约发行的ICO的状态
# Vyper does not allow for dynamic arrays，we have limited the number of ICO
allIcoAddressOfUser: public(map(address, address[MAX_NUMBER]))
# the ico amount of each account
allIcoCountsOfUser: public(map(address, int128))
allIcoCreater: public(map(address, address))  # 所有ICO创建者的地址，用来发给它稳定币
submitssionDelta: public(timedelta)  # ICO结束后到最后提交时间间隔，可以设置，暂时定为72小时
setter: public(address)  # 设定上述时间间隔的地址


@public
def __init__():
    self.setter = msg.sender
    self.submitssionDelta = 3 * 24 * 3600


@public
def setNewSetter(_newSetter: address):
    assert _newSetter != ZERO_ADDRESS
    assert msg.sender == self.setter
    log.NewSetter(self.setter, _newSetter)
    self.setter = _newSetter


@public
def setSubmitssionDelta(_newDelta: timedelta):
    assert _newDelta > 0
    assert msg.sender == self.setter
    self.submitssionDelta = _newDelta
    log.NewSubmitDelta(_newDelta)


# 设置模板地址和接收ETH地址
@public
def initializeFactory(template: address, _beneficiary: address, _ndaoAddress: address, _queryAddress: address, _icoAddress: address):
    assert self.exchangeTemplate == ZERO_ADDRESS and self.beneficiary == ZERO_ADDRESS
    assert self.ndaoAddress == ZERO_ADDRESS and self.queryAddress == ZERO_ADDRESS
    assert self.icoTemplate == ZERO_ADDRESS
    assert template != ZERO_ADDRESS and _beneficiary != ZERO_ADDRESS
    assert _ndaoAddress != ZERO_ADDRESS and _queryAddress != ZERO_ADDRESS
    assert _icoAddress != ZERO_ADDRESS
    self.exchangeTemplate = template
    self.beneficiary = _beneficiary
    self.ndaoAddress = _ndaoAddress
    self.queryAddress = _queryAddress
    self.icoTemplate = _icoAddress


@public
def createICO(_name: string[64], _symbol: string[32], _decimals: uint256, _depositGoal: uint256, _delta: timedelta, _price: uint256):
    assert self.icoTemplate != ZERO_ADDRESS
    assert self.allIcoCountsOfUser[msg.sender] < MAX_NUMBER
    ico: address = create_forwarder_to(self.icoTemplate)
    assert self.allIcoStatus[ico] == STATUS_NONE
    ICO(ico).setup(_name, _symbol, _decimals, _depositGoal,
                   _delta, self.submitssionDelta, _price, msg.sender)
    index: int128 = self.allIcoCountsOfUser[msg.sender]
    self.allIcoCountsOfUser[msg.sender] = index + 1
    self.allIcoAddressOfUser[msg.sender][index] = ico
    self.allIcoStatus[ico] = STATUS_STARTED
    self.allIcoCreater[ico] = msg.sender
    log.ICOCreated(msg.sender, ico)


@public
def endIco():
    if self.allIcoStatus[msg.sender] == STATUS_STARTED:
        self.allIcoStatus[msg.sender] = STATUS_FAILED


@public
@constant
def getLatestIco() -> address:
    count: int128 = self.allIcoCountsOfUser[msg.sender]
    if count > 0:
        return self.allIcoAddressOfUser[msg.sender][count - 1]
    else:
        return ZERO_ADDRESS


# 计算ETH对应的NDAO数量
@private
@constant
def _calNdaoAmount(eth_amount: wei_value) -> uint256:
    price: uint256 = QueryEthPrice(self.queryAddress).getEthPrice()
    result: uint256 = as_unitless_number(
        eth_amount) * 10**(NDAO(self.ndaoAddress).decimals() - 2) / price
    return result



# 直接通过ETH购买NDAO
# todo 收益人未确定
@public
@payable
def buyNdao() -> uint256:
    send(self.beneficiary, msg.value)
    amount:uint256 = self._calNdaoAmount(msg.value)
    NDAO(self.ndaoAddress).mint(msg.sender, amount)
    return amount


@private
def _saveExchangeInfo(token: address, exchange: address):
    # token和对应的合约相互map
    self.token_to_exchange[token] = exchange
    self.exchange_to_token[exchange] = token
    # 编号并保存token
    token_id: uint256 = self.tokenCount + 1
    self.tokenCount = token_id
    self.id_to_token[token_id] = token


@public
@payable
def createExchange():
    assert self.exchangeTemplate != ZERO_ADDRESS
    assert self.token_to_exchange[msg.sender] == ZERO_ADDRESS
    assert self.allIcoStatus[msg.sender] == STATUS_STARTED
    assert self.allIcoCreater[msg.sender] != ZERO_ADDRESS
    self.allIcoStatus[msg.sender] = STATUS_SUCCESS
    # 创建交易合约并设置token
    exchange: address = create_forwarder_to(self.exchangeTemplate)
    token_amount: uint256 = ERC20(msg.sender).balanceOf(self)
    # 发送代币
    flag: bool = ERC20(msg.sender).transfer(exchange, token_amount)
    assert flag
    # 发送ETH到仓库地址
    send(self.beneficiary, msg.value)
    # 设置交易对合约
    Exchange(exchange).setup(msg.sender, self.ndaoAddress, token_amount)
    # 增发稳定币,创建得和交易对各1倍
    ndao_amount: uint256 = self._calNdaoAmount(msg.value)
    NDAO(self.ndaoAddress).mint(exchange, ndao_amount)
    NDAO(self.ndaoAddress).mint(self.allIcoCreater[msg.sender], ndao_amount)
    self._saveExchangeInfo(msg.sender, exchange)
    log.NewExchange(msg.sender, exchange, ndao_amount, token_amount)


# 获取一个token对应的交易对合约地址
@public
@constant
def getExchange(token: address) -> address:
    return self.token_to_exchange[token]


# 根据对应的合约地址获取token
@public
@constant
def getToken(exchange: address) -> address:
    return self.exchange_to_token[exchange]


# 通过ID获得token地址
@public
@constant
def getTokenWithId(token_id: uint256) -> address:
    return self.id_to_token[token_id]
