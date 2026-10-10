// ORD-0572: this domain's slice of ../LocaleContext.tsx, moved verbatim -- no value was reworded.

export const lib = {
  en: {
  /* ORD-0557: the attribution titles `lib/failureAttribution.ts` writes inline. Key names and English
     arms are copied from the CN draft table verbatim; both arms are the bytes those screens already
     showed, so the move cannot change what a traveller reads. */
  "lib.failureAttribution.tripNotOnServer": "This trip is not on this server",
  "lib.failureAttribution.networkUnavailable": "Network unavailable",
  "lib.failureAttribution.serviceUnavailable": "The service is temporarily unavailable",
  "lib.failureAttribution.serverCouldNotRead": "The server could not read your trip",
  "lib.failureAttribution.slowDownRate": "The server asked us to slow down",
  "lib.failureAttribution.slowDownRetry": "The server asked us to slow down",
  "lib.failureAttribution.stateAlreadyMoved": "The state already moved - this was not a failed read",
  "lib.failureAttribution.needsFreshSignIn": "This trip needs a fresh sign-in",
  "lib.failureAttribution.stepNotAllowed": "This server will not allow this step",
  "lib.failureAttribution.readFailed": "This read failed",
  "lib.displayVocabulary.nativeGatewayAnswering": "the native gateway installed on this machine is answering",
  "lib.displayVocabulary.compatEndpointUnverified": "the compatibility endpoint this deployment configured; no verified native gateway",
  "lib.displayVocabulary.serviceOwnLoop": "this service's own loop straight to the model provider",
  },
  zh: {
  /* ORD-0557：`lib/failureAttribution.ts` 里那些直接写在源码上的归因小标题。键名与英文臂逐字照 CN
     草稿表抄；中文臂就是屏上此刻在显示的那串字，这是搬运不是改写。 */
  "lib.failureAttribution.tripNotOnServer": "这台服务器上没有这一趟行程了",
  "lib.failureAttribution.networkUnavailable": "网络不可用",
  "lib.failureAttribution.serviceUnavailable": "服务暂时不可用",
  "lib.failureAttribution.serverCouldNotRead": "服务器这次没能把行程读出来",
  "lib.failureAttribution.slowDownRate": "服务器请我们慢一点",
  "lib.failureAttribution.slowDownRetry": "服务器请我们慢一点",
  "lib.failureAttribution.stateAlreadyMoved": "这件事的状态已经变了，不是没读到",
  "lib.failureAttribution.needsFreshSignIn": "这一趟需要重新登录才能读",
  "lib.failureAttribution.stepNotAllowed": "这一步这台服务器不允许",
  "lib.failureAttribution.readFailed": "这一次没读到",
  "lib.displayVocabulary.nativeGatewayAnswering": "本机自带的原生网关正在应答",
  "lib.displayVocabulary.compatEndpointUnverified": "这台部署配的兼容端点，原生网关没有验到在应答",
  "lib.displayVocabulary.serviceOwnLoop": "这个服务自己直连模型商的那条环",
  },
};
