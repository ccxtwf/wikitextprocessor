from typing import Literal, Any

MAX_TEMPLATE_EXPIRATION=14*24*60*60   # 14 days, in seconds

VLW_LIVE_WIKI_DOMAIN="https://vocaloidlyrics.miraheze.org"
VLW_API_SCRIPT_PATH="/w/api.php"
META_MH_LIVE_WIKI_DOMAIN="https://meta.miraheze.org"
META_MH_API_SCRIPT_PATH="/w/api.php"
MAX_WIKI_REQUEST_ATTEMPTS=3

ParserFunctionConfigKeys = Literal["MAX_LOOPS_ITER"]
ParserFunctionConfig: dict[ParserFunctionConfigKeys, Any] = {
  "MAX_LOOPS_ITER": 100
}
