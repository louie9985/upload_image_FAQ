import React from 'react';
import { Card, Typography } from 'antd';

const { Title, Paragraph, Text } = Typography;

export function UserManual() {
  return (
    <div className="userManual">
      <Card className="dataCard">
        <Title level={4}>欢迎使用</Title>
        <Paragraph type="secondary">
          本平台用于批量上传图片、基于描述调用大模型生成问答，并将结果同步到企业微信智能表格。登录后主要使用「新建任务」「历史任务」「上传记录」「Token
          用量」等标签页。
        </Paragraph>
      </Card>

      <Card className="dataCard" title="一、图片与格式">
        <Paragraph>
          仅支持 <Text strong>PNG、JPG、JPEG</Text>。请勿使用 SVG（与微信小程序等产品不兼容）。上传时可一次多选。
        </Paragraph>
      </Card>

      <Card className="dataCard" title="二、新建任务流程">
        <Paragraph>
          <Text strong>1. 创建任务并上传</Text>
          <br />
          可选填任务标题 → 选择图片 → 点击「创建任务并上传」。
        </Paragraph>
        <Paragraph>
          <Text strong>2. 填写描述</Text>
          <br />
          每张图必须填写描述。若多张图共同表达一条知识（如证书正反面），可勾选至少两张图，点击「新增合并项」，并为合并项单独填写描述。合并项会额外生成问答，不替代单图项。
        </Paragraph>
        <Paragraph>
          <Text strong>3. 生成问答</Text>
          <br />
          点击「保存描述并生成问答」，在弹窗中查看进度；可关闭弹窗，任务仍会继续。
        </Paragraph>
        <Paragraph>
          <Text strong>4. 审核与上传</Text>
          <br />
          修改主问题、相似问题（每行一条）、答案；可逐条「保存当前修改」。填写企业微信智能表格的 Webhook 链接后，点击「上传到 webhook」。若未逐条保存，上传前系统会自动保存页面上的修改。
        </Paragraph>
        <Paragraph type="secondary">
          「一键清空」只清空当前页面临时内容，不会删除历史任务或上传记录。
        </Paragraph>
      </Card>

      <Card className="dataCard" title="三、其他标签页">
        <Paragraph>
          <Text strong>历史任务</Text>：查看所有批次状态、图片数、处理进度与创建时间。
        </Paragraph>
        <Paragraph>
          <Text strong>上传记录</Text>：查看每次上传的结果、企业微信记录信息及图片 CDN 链接。
        </Paragraph>
        <Paragraph>
          <Text strong>Token 用量</Text>：查看当前账号大模型调用的累计 Token 与最近明细。
        </Paragraph>
      </Card>

      <Card className="dataCard" title="四、常见问题">
        <Paragraph>生成或上传失败时，请在进度弹窗中查看失败原因；检查描述、网络与 Webhook 地址，仍无法解决请联系管理员。</Paragraph>
        <Paragraph type="secondary">完整说明见项目文档 docs/user-manual.md。</Paragraph>
      </Card>
    </div>
  );
}
