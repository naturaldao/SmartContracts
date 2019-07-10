# @dev Implementation of ico for ERC-20 token .
# @author radarzhhua@gmail.com
# @refernce https://github.com/ethereum/EIPs/blob/master/EIPS/eip-20.md
from vyper.interfaces import ERC20
implements: ERC20


# define the Factory contract
contract Factory:
    def createExchange(): modifying
    def endIco(): modifying

ETHER_TO_WEI: constant(uint256) = 10 ** 18

# event of ERC-20
Transfer: event(
    {_from: indexed(address), _to: indexed(address), _value: uint256})
Approval: event({_owner: indexed(address),
                 _spender: indexed(address), _value: uint256})
# event of ICO
GoalReached: event({_goalTime: timestamp, _depositGoal: wei_value})
RefundTransfer: event({_owner: indexed(address), _amount: wei_value})


# ERC20 state varialbes
name: public(string[64])  # 代币名称
symbol: public(string[32])  # 代币名称简写
decimals: public(uint256)  # 精度
balanceOf: public(map(address, uint256))  # 每个账户余额
allowances: map(address, map(address, uint256))  # 每个账号的授权情况
total_supply: uint256  # 总发行量
# ICO state varialbes

depositGoal: public(wei_value)  # ICO募资目标
depositStart: public(timestamp)  # ICO开始时间
depositEnd: public(timestamp)  # ICO结束时间
finalSubmissionTime: public(timestamp)  # ICO最后提交验证截止时间
isEnd: public(bool)  # ICO是否结束
goalReached: public(bool)  # ICO是否目标达成
isFailed: public(bool)  # ICO是否失败
# 发行ICO时token价格，1ETH兑换多少token，暂未考虑发行token价格高于ETH的情况
tokenPrice: public(uint256)
depositAmount: public(wei_value)  # 当前已经募资总量
depositBalanceOfUser: public(map(address, wei_value))  # 记录每个投资者的投资资金
factory: public(address)  # factory合约地址，用来接受ICO
creater: public(address)   # ICO申请者,用来提交ICO或者取消ICO


@public
def setup(_name: string[64], _symbol: string[32], _decimals: uint256, _depositGoal: uint256,
          _deltaOfEnd: timedelta, _deltaOfSubmitssion: timedelta, token_price: uint256, _creater: address):
    """
    @dev init the contract.
    @notice the method is called once right after the contract is deployed
    @param _name the name string of token
    @param _symbol the symbol string of token
    @param _decimals the decimals of token
    @param _depositGoal the amout of Ethers(WEI) that can deposit in the ICO
    @param _deltaOfEnd the duration of ICO (second)
    @param _deltaOfSubmitssion the duration between depositEnd and finalSubmissionTime
    @param token_price the amount of token that one ether can exchange
    """
    assert self.factory == ZERO_ADDRESS and _creater != ZERO_ADDRESS
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals
    self.depositGoal = as_wei_value(_depositGoal, 'wei')
    self.depositStart = block.timestamp
    self.depositEnd = self.depositStart + _deltaOfEnd
    self.finalSubmissionTime = self.depositEnd + _deltaOfSubmitssion
    self.tokenPrice = token_price
    self.creater = _creater
    self.factory = msg.sender


@public
@constant
def totalSupply() -> uint256:
    """
    @dev Total number of tokens in existence.
    """
    return self.total_supply


@public
@constant
def allowance(_owner: address, _spender: address) -> uint256:
    """
    @dev Function to check the amount of tokens that an owner allowed to a spender.
    @param _owner The address which owns the funds.
    @param _spender The address which will spend the funds.
    @return An uint256 specifying the amount of tokens still available for the spender.
    """
    return self.allowances[_owner][_spender]


@public
def transfer(_to: address, _value: uint256) -> bool:
    """
    @dev Transfer token for a specified address
    @param _to The address to transfer to.
    @param _value The amount to be transferred.
    """
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    log.Transfer(msg.sender, _to, _value)
    return True


@public
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    """
     @dev Transfer tokens from one address to another.
          Note that while this function emits a Transfer event, this is not required as per the specification,
          and other compliant implementations may not emit the event.
     @param _from address The address which you want to send tokens from
     @param _to address The address which you want to transfer to
     @param _value uint256 the amount of tokens to be transferred
    """
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowances[_from][msg.sender] -= _value
    log.Transfer(_from, _to, _value)
    return True


@public
def approve(_spender: address, _value: uint256) -> bool:
    """
    @dev Approve the passed address to spend the specified amount of tokens on behalf of msg.sender.
         Beware that changing an allowance with this method brings the risk that someone may use both the old
         and the new allowance by unfortunate transaction ordering. One possible solution to mitigate this
         race condition is to first reduce the spender's allowance to 0 and set the desired value afterwards:
         https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    @param _spender The address which will spend the funds.
    @param _value The amount of tokens to be spent.
    """
    self.allowances[msg.sender][_spender] = _value
    log.Approval(msg.sender, _spender, _value)
    return True


@private
def mint(_to: address, _value: uint256):
    """
    @dev Mint an amount of the token and assigns it to an account.
         This encapsulates the modification of balances such that the
         proper events are emitted.
    @notice It can only be called internally at depositing or at the ending of a successful ico
            when the ico is not ended
    @param _to The account that will receive the created tokens.
    @param _value The amount that will be created.
    """
    assert _to != ZERO_ADDRESS
    self.total_supply += _value
    self.balanceOf[_to] += _value
    log.Transfer(ZERO_ADDRESS, _to, _value)


@private
def _checkDeposit(sender: address, value: wei_value):
    """
    @dev Receive the ether and mint proper tokens
    @param value The account of the ether.
    @param sender The address that prepare to be minted .
    """
    assert block.timestamp <= self.depositEnd, 'the ico has timeout'
    assert not self.goalReached, 'the ico has completed'
    if self.depositAmount + value >= self.depositGoal:
        self.goalReached = True
        _refund: wei_value = self.depositAmount + value - self.depositGoal
        _deposit_amount: wei_value = self.depositGoal - self.depositAmount
        self.depositAmount += _deposit_amount
        self.depositBalanceOfUser[sender] += _deposit_amount
        _token_amount: uint256 = as_unitless_number(
            _deposit_amount) * self.tokenPrice / ETHER_TO_WEI
        self.mint(sender, _token_amount)
        send(sender, _refund)
        log.GoalReached(block.timestamp, self.depositGoal)
    else:
        self.depositBalanceOfUser[sender] += value
        self.depositAmount += value
        _token_amount: uint256 = as_unitless_number(
            value) * self.tokenPrice / ETHER_TO_WEI
        self.mint(sender, _token_amount)


@public
@payable
def __default__():
    """
    @dev  sent Ether(without data).
    """
    self._checkDeposit(msg.sender, msg.value)


@public
@payable
def deposit():
    """
    @dev  sent Ether(with data).
    """
    self._checkDeposit(msg.sender, msg.value)


@public
def cancelICO():
    """
    @dev  cancel the ICO ,this is called only once by creater  before ended or by anyonde after finalSubmissionTime
    """
    assert block.timestamp > self.depositEnd and (not self.isFailed)
    self.isFailed = True
    self.isEnd = True
    if block.timestamp <= self.finalSubmissionTime:
        assert msg.sender == self.creater
        Factory(self.factory).endIco()
    else:
        Factory(self.factory).endIco()


@public
def submitICO():
    """
    @dev  submit the ICO  only once by creater
    """
    assert block.timestamp > self.depositEnd and  block.timestamp < self.finalSubmissionTime
    assert msg.sender == self.creater and (not self.isEnd)
    self.isEnd = True
    if self.goalReached:
        self.mint(self.factory, self.total_supply)
        Factory(self.factory).createExchange(value=self.depositGoal)
    else:
        self.isFailed = True
        Factory(self.factory).endIco()


@public
def safeWithdrawal():
    """
    @dev when ico is ended and failed,the user withdraws their deposit ethers.
          this function is using the withdrawal pattern.
    """
    assert self.isEnd and self.isFailed, 'the ico has not ended or the ico is successful'
    amount: wei_value = self.depositBalanceOfUser[msg.sender]
    self.depositBalanceOfUser[msg.sender] = 0
    send(msg.sender, amount)
    log.RefundTransfer(msg.sender, amount)


@private
def _burn(_to: address, _value: uint256):
    """
    @dev Internal function that burns an amount of the token of a given
         account.
    @param _to The account whose tokens will be burned.
    @param _value The amount that will be burned.
    """
    assert _to != ZERO_ADDRESS
    self.total_supply -= _value
    self.balanceOf[_to] -= _value
    log.Transfer(_to, ZERO_ADDRESS, _value)


@public
def burn(_value: uint256):
    """
    @dev Burn an amount of the token of msg.sender.
    @param _value The amount that will be burned.
    """
    self._burn(msg.sender, _value)


@public
def burnFrom(_to: address, _value: uint256):
    """
    @dev Burn an amount of the token from a given account.
    @param _to The account whose tokens will be burned.
    @param _value The amount that will be burned.
    """
    self.allowances[_to][msg.sender] -= _value
    self._burn(_to, _value)
