from lib.rbk import core, logger


core.Init("pyAppTest")

msg = "test"
logger.LogDebug(msg)
logger.LogInfo(msg)
logger.LogWarn(msg)
logger.LogError(msg)
logger.LogFatal(msg)
