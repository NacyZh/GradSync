import { messagesEn } from '@/data/locale/messages.en';
import { messagesZh } from '@/data/locale/messages.zh';
import { runtimeZh } from '@/data/locale/runtime.zh';

const keyedZhByEnglish = Object.fromEntries(
  Object.entries(messagesEn).map(([key, value]) => [value, messagesZh[key as keyof typeof messagesZh]]),
) as Record<string, string>;

export function activeUiLocale() {
  if (typeof window === 'undefined') return 'en';
  return window.localStorage.getItem('gradsync.locale') === 'zh' ? 'zh' : 'en';
}

export function formatUiDate(
  value: string | number | Date,
  options?: Intl.DateTimeFormatOptions,
) {
  const locale = activeUiLocale() === 'zh' ? 'zh-CN' : 'en';
  return new Intl.DateTimeFormat(locale, options).format(new Date(value));
}

export function translateUiText(value: string, locale = activeUiLocale()) {
  if (locale !== 'zh') return value;
  const exact = runtimeZh[value] ?? keyedZhByEnglish[value];
  if (exact) return exact;
  return value
    .replace(/^(\d+) (document|code|paper) materials$/, (_, count: string, type: string) => `${count} 份${materialTypeZh[type]}材料`)
    .replace(/^Show (Document|Code|Paper) materials$/, (_, type: string) => `显示${materialTypeZh[type.toLowerCase()]}材料`)
    .replace(/^Search (document|code|paper) materials$/, (_, type: string) => `搜索${materialTypeZh[type]}材料`)
    .replace(/^No (document|code|paper) materials match the current search\.$/, (_, type: string) => `没有符合当前搜索条件的${materialTypeZh[type]}材料。`)
    .replace(/^(document|code|paper) material results$/, (_, type: string) => `${materialTypeZh[type]}材料结果`)
    .replace(/^(document|code|paper) · (active|pending review|approved|rejected|archived)$/, (_, type: string, state: string) => `${materialTypeZh[type]} · ${materialStateZh[state]}`)
    .replace(/^Category (.+)$/, '分类 $1')
    .replace(/^Select document (.+)$/, '选择文档 $1')
    .replace(/^Download (?!started:|ready:)(.+)$/, '下载 $1')
    .replace(/^Maximum (\d+) for (.+)$/, '最大可用数量 $1（$2）')
    .replace(/^(\d+) of (\d+) available · (\d+) in use$/, '$2 件中 $1 件可用 · $3 件使用中')
    .replace(/^(\d+) available · (\d+) allocated · (\d+) total$/, '$1 件可用 · $2 件已分配 · 共 $3 件')
    .replace(/^(\d+) available$/, '$1 件可用')
    .replace(/^(\d+) conflicts?$/, '$1 个冲突')
    .replace(/^(\d+) periods?$/, '$1 个时段')
    .replace(/^Qty (\d+)$/, '数量 $1')
    .replace(/^Student #(\d+) · student request$/, '学生 #$1 · 学生申请')
    .replace(/^Student #(\d+)$/, '学生 #$1')
    .replace(/^(.+) · student request$/, '$1 · 学生申请')
    .replace(/^\+(\d+) more$/, '还有 $1 项')
    .replace(/^(\d+) scheduled items?$/, '$1 项日程')
    .replace(/^(\d+) items?$/, '$1 项')
    .replace(/^View all (\d+) schedules on (.+)$/, '查看 $2 的全部 $1 项日程')
    .replace(/^Schedules on (.+)$/, '$1 的日程')
    .replace(/^Filter calendar sources, (\d+) selected$/, '筛选日历来源，已选择 $1 项')
    .replace(/^(\d+) visible workspaces$/, '$1 个可见工作区')
    .replace(/^(\d+) visible$/, '$1 条可见')
    .replace(/^(\d+) active$/, '$1 个活跃')
    .replace(/^(\d+) suspended$/, '$1 个已停用')
    .replace(/^(\d+) admins$/, '$1 个管理员')
    .replace(/^(\d+) pending$/, '$1 个待处理')
    .replace(/^(\d+) skipped$/, '$1 个已跳过')
    .replace(/^(\d+) needs retry$/, '$1 个需要重试')
    .replace(/^Project #(\d+)$/, '项目 #$1')
    .replace(/^(\d+)% complete$/, '已完成 $1%')
    .replace(/^Priority: (low|normal|high|urgent)$/, (_, priority: string) => `优先级：${({ low: '低', normal: '普通', high: '高', urgent: '紧急' } as Record<string, string>)[priority]}`)
    .replace(/^Review progress_report #(\d+)$/, '评审进展汇报 #$1')
    .replace(/^Version (\d+)$/, '版本 $1')
    .replace(/^Last attempt (.+)$/, '上次尝试 $1')
    .replace(/^Sent (.+)$/, '已发送 $1')
    .replace(/^Eligible (.+)$/, '可投递时间 $1')
    .replace(/^Submitted (.+)$/, '提交于 $1')
    .replace(/^Availability observed (.+)$/, '可用情况更新于 $1')
    .replace(/^Starts (.+)$/, '开始于 $1')
    .replace(/^Ends (.+)$/, '结束于 $1')
    .replace(/^Next due (.+)$/, '下一截止日期 $1')
    .replace(/^Retry needed \((\d+)\)$/, '需要重试（$1）')
    .replace(/^Week (.+?) · Revision (\d+)$/, '第 $1 周 · 修订 $2')
    .replace(/^Week (.+)$/, '第 $1 周')
    .replace(/^Download started: (.+)$/, '下载已开始：$1')
    .replace(/^Download ready: (.+)$/, '下载已就绪：$1')
    .replace(/^Created project (.+)$/, '已创建项目 $1')
    .replace(/^Weekly report deadline saved for (.+)$/, '周期汇报截止时间已保存：$1')
    .replace(/^Choose a supported archive file: (.+)\.$/, '请选择支持的压缩包格式：$1。')
    .replace(/^Choose an archive no larger than (.+)\.$/, '请选择不超过 $1 的压缩包。')
    .replace(/^(.+) exceeds the (.+) upload size limit\.$/, '$1 超过了 $2 的上传大小限制。')
    .replace(/^Quantity cannot exceed (\d+)\.$/, '数量不能超过 $1。');
}

const materialTypeZh: Record<string, string> = {
  document: '文档',
  code: '代码',
  paper: '论文',
};

const materialStateZh: Record<string, string> = {
  active: '有效',
  'pending review': '待评审',
  approved: '已批准',
  rejected: '已拒绝',
  archived: '已归档',
};

const apiMessages: Record<string, string> = {
  'Invalid email or password.': '邮箱或密码错误。',
  'This account is not active. Contact an administrator.': '账号尚未激活，请联系管理员。',
  'An account with this email already exists.': '该邮箱已注册。',
  'Invalid or expired verification code.': '验证码无效或已过期。',
  'Current password is incorrect.': '当前密码错误。',
  'New password must be different from the current password.': '新密码不能与当前密码相同。',
  'Name is required.': '姓名为必填项。',
  'Nickname is required.': '昵称为必填项。',
  'Student registration requires a masters or doctoral degree type.': '学生注册必须选择硕士或博士。',
  'Requested role must be student or teacher.': '申请角色只能是学生或教师。',
  'If the account is awaiting verification, a new code has been sent.': '如果账号正在等待验证，新的验证码已发送。',
};

export function translateApiMessage(value: string) {
  if (activeUiLocale() !== 'zh') return value;
  if (apiMessages[value]) return apiMessages[value];
  if (value.startsWith('Password must contain ')) return '密码必须至少八位，并包含大小写字母、数字和符号。';
  return translateUiText(value, 'zh');
}
