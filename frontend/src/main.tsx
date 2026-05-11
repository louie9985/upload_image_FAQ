import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import {
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  Image,
  Input,
  Layout,
  List,
  Modal,
  Progress,
  Row,
  Space,
  Table,
  Tabs,
  Tooltip,
  Typography,
  Upload,
  message,
} from 'antd';
import type { UploadFile } from 'antd';
import 'antd/dist/reset.css';
import './styles.css';
import { api } from './api';
import type { BatchJob, FaqDraft, GenerationItemDraft, LlmUsageSummary, ProgressState, UploadedImage, UploadRecord, User } from './types';
import { UserManual } from './UserManual';

const { Header, Content } = Layout;

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [activeTab, setActiveTab] = useState('new');

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoadingUser(false));
  }, []);

  const onLogout = async () => {
    try {
      await api.logout();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '退出失败');
    } finally {
      setUser(null);
      setActiveTab('new');
    }
  };

  if (loadingUser) return <div className="center">加载中...</div>;
  if (!user) {
    return (
      <div className="loginPage">
        <LoginCard onLogin={setUser} />
      </div>
    );
  }

  return (
    <Layout className="app">
      <Header className="header">
        <div className="brandBlock">
          <div className="brandLogo">FAQ</div>
          <div className="brandMeta">
            <Typography.Title level={4} className="title">
              图片问答上传平台
            </Typography.Title>
            <span className="brandEyebrow">企业知识问答工具</span>
          </div>
        </div>
        <Space size="middle">
          <span className="user">{user.name || user.username}</span>
          <Button onClick={onLogout}>退出</Button>
        </Space>
      </Header>
      <Content className="content">
        <div className="pageShell">
          <Card className="heroCard">
            <div className="heroContent">
              <div>
                <Typography.Title level={3} className="heroTitle">
                  批量生成图片问答，沉淀企业知识
                </Typography.Title>
                <Typography.Text className="sectionSubtitle">
                  上传图片、组合多图材料、调用大模型生成问答，并同步到企业微信智能表格。
                </Typography.Text>
                <div className="workflowPills">
                  <span className="pill">图片上传</span>
                  <span className="pill">多图合并</span>
                  <span className="pill">AI 生成</span>
                  <span className="pill">Webhook 上传</span>
                </div>
              </div>
              <div className="heroActions">
                <Button type="primary" onClick={() => setActiveTab('new')}>
                  开始新任务
                </Button>
                <Button onClick={() => setActiveTab('records')}>查看上传记录</Button>
              </div>
            </div>
          </Card>
          <div className="tabsCard">
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                { key: 'new', label: '新建任务', children: <NewBatch /> },
                { key: 'history', label: '历史任务', children: <BatchHistory /> },
                { key: 'records', label: '上传记录', children: <UploadRecords /> },
                { key: 'usage', label: 'Token 用量', children: <TokenUsage /> },
                { key: 'manual', label: '使用手册', children: <UserManual /> },
              ]}
            />
          </div>
        </div>
      </Content>
    </Layout>
  );
}

function LoginCard({ onLogin }: { onLogin: (user: User) => void }) {
  const [loading, setLoading] = useState(false);

  const submit = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const loggedInUser = await api.login(values.username, values.password);
      onLogin(loggedInUser);
      message.success('登录成功');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="loginCard">
      <div className="loginBrand">
        <span className="brandEyebrow">Enterprise FAQ Builder</span>
        <Typography.Title level={3}>图片问答上传平台</Typography.Title>
        <Typography.Paragraph type="secondary">登录后可批量生成问答、审核结果并上传到企业微信智能表格。</Typography.Paragraph>
      </div>
      <Form layout="vertical" onFinish={submit} initialValues={{ username: 'admin' }}>
        <Form.Item name="username" label="账号" rules={[{ required: true, message: '请输入账号' }]}>
          <Input autoComplete="username" />
        </Form.Item>
        <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
          <Input.Password autoComplete="current-password" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block>
          登录
        </Button>
      </Form>
    </Card>
  );
}

function NewBatch() {
  const [title, setTitle] = useState('');
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [batch, setBatch] = useState<BatchJob | null>(null);
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [drafts, setDrafts] = useState<FaqDraft[]>([]);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [progressRunKey, setProgressRunKey] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dirtyDraftIds, setDirtyDraftIds] = useState<Set<number>>(new Set());
  const [uploadRecords, setUploadRecords] = useState<UploadRecord[]>([]);
  const [activeOperation, setActiveOperation] = useState<'generate' | 'webhook' | null>(null);
  const [progressModalOpen, setProgressModalOpen] = useState(false);
  const [selectedImageIds, setSelectedImageIds] = useState<Set<number>>(new Set());
  const [generationItems, setGenerationItems] = useState<GenerationItemDraft[]>([]);

  useProgress(batch?.id, progressRunKey, setProgress, async (next) => {
    setGenerating(false);
    setUploading(false);
    if (!batch) return;
    setDrafts(await api.getDrafts(batch.id));
    if (next.status === 'completed' || next.status === 'failed') {
      setUploadRecords(await api.listUploadRecords());
    }
    if (next.status === 'generated') message.success('问答生成完成');
    if (next.status === 'completed') message.success('Webhook 上传完成');
    if (next.status === 'failed') message.error(next.error_message || '任务处理失败');
  });

  const clearWorkspace = () => {
    setTitle('');
    setFileList([]);
    setBatch(null);
    setImages([]);
    setProgress(null);
    setDrafts([]);
    setWebhookUrl('');
    setProgressRunKey(0);
    setGenerating(false);
    setUploading(false);
    setDirtyDraftIds(new Set());
    setUploadRecords([]);
    setActiveOperation(null);
    setProgressModalOpen(false);
    setSelectedImageIds(new Set());
    setGenerationItems([]);
    message.success('已清空当前上传页');
  };

  const createAndUpload = async () => {
    const files = fileList.map((item) => item.originFileObj).filter(Boolean) as File[];
    if (!files.length) {
      message.warning('请先选择图片');
      return;
    }
    const createdBatch = await api.createBatch(title || `图片问答任务 ${new Date().toLocaleString()}`);
    const uploaded = await api.uploadImages(createdBatch.id, files);
    setBatch(createdBatch);
    setImages(uploaded);
    setGenerationItems(
      uploaded.map((image, index) => ({
        id: `single-${image.id}`,
        image_ids: [image.id],
        title: `${index + 1}`,
        description: image.description || '',
        sort_order: index,
        is_combined: false,
      })),
    );
    setProgress(null);
    setDrafts([]);
    setUploadRecords([]);
    setSelectedImageIds(new Set());
    message.success('图片已上传，请填写每张图片描述');
  };

  const saveDescriptionsAndGenerate = async () => {
    const missing = generationItems.filter((item) => !item.description.trim());
    if (missing.length) {
      message.error('每个单图项和合并项都必须填写描述');
      return;
    }
    try {
      setGenerating(true);
      setActiveOperation('generate');
      setProgress({
        id: batch?.id || 0,
        status: 'generating',
        total_count: generationItems.length,
        processed_count: 0,
        failed_count: 0,
        current_step: '正在保存描述和生成项...',
        error_message: '',
        percent: 0,
      });
      setProgressModalOpen(true);
      await Promise.all(
        generationItems
          .filter((item) => !item.is_combined)
          .map((item) => api.updateImageDescription(item.image_ids[0], item.description)),
      );
      if (batch) {
        await api.saveGenerationItems(batch.id, generationItems);
        setProgressRunKey((value) => value + 1);
        await api.startGenerate(batch.id);
        message.success('已开始生成问答，请等待完成');
      }
    } catch (error) {
      setGenerating(false);
      setProgressModalOpen(false);
      message.error(error instanceof Error ? error.message : '启动生成失败');
    }
  };

  const createCombinedGenerationItem = () => {
    const selectedImages = images.filter((image) => selectedImageIds.has(image.id));
    if (selectedImages.length < 2) {
      message.warning('请至少勾选两张图片新增合并项');
      return;
    }
    const toBaseName = (name: string) => {
      const trimmed = name.trim();
      const noExt = trimmed.replace(/\.(png|jpe?g|webp|gif|bmp|tiff?)$/i, '');
      return noExt.replace(/\s*\(\d+\)\s*$/g, '').replace(/\s*副本\s*$/g, '').trim();
    };

    const toImageLabel = (image: UploadedImage) => {
      const base = toBaseName(image.original_name || '');
      if (base) return base.length > 16 ? `${base.slice(0, 16)}…` : base;
      const idx = images.findIndex((item) => item.id === image.id);
      return idx >= 0 ? `图片${idx + 1}` : `图片${image.id}`;
    };

    const titleParts = selectedImages.map(toImageLabel);
    const title =
      titleParts.length <= 3
        ? `合并：${titleParts.join(' + ')}`
        : `合并：${titleParts.slice(0, 2).join(' + ')} + 等${titleParts.length}张`;
    const description = selectedImages
      .map((image) => generationItems.find((item) => !item.is_combined && item.image_ids[0] === image.id)?.description)
      .filter(Boolean)
      .join('\n');
    setGenerationItems((items) => [
      ...items,
      {
        id: `${Date.now()}`,
        image_ids: selectedImages.map((image) => image.id),
        title,
        description,
        sort_order: items.length,
        is_combined: true,
      },
    ]);
    setSelectedImageIds(new Set());
    message.success(`已新增 ${title}`);
  };

  const saveDirtyDrafts = async () => {
    const dirtyDrafts = drafts.filter((draft) => dirtyDraftIds.has(draft.id));
    if (!dirtyDrafts.length) return drafts;
    const savedDrafts = await Promise.all(dirtyDrafts.map(api.updateDraft));
    const savedMap = new Map(savedDrafts.map((draft) => [draft.id, draft]));
    const nextDrafts = drafts.map((draft) => savedMap.get(draft.id) || draft);
    setDrafts(nextDrafts);
    setDirtyDraftIds(new Set());
    message.success('已自动保存当前修改');
    return nextDrafts;
  };

  const uploadWebhook = async () => {
    if (!batch || !webhookUrl.trim()) {
      message.warning('请填写 webhook 链接');
      return;
    }
    try {
      setUploading(true);
      setActiveOperation('webhook');
      setProgress({
        id: batch.id,
        status: 'uploading',
        total_count: drafts.length,
        processed_count: 0,
        failed_count: 0,
        current_step: '正在保存修改并准备上传...',
        error_message: '',
        percent: 0,
      });
      setProgressModalOpen(true);
      await saveDirtyDrafts();
      setProgressRunKey((value) => value + 1);
      await api.uploadWebhook(batch.id, webhookUrl);
      message.success('已开始上传 webhook，请等待完成');
    } catch (error) {
      setUploading(false);
      setProgressModalOpen(false);
      message.error(error instanceof Error ? error.message : '启动 webhook 上传失败');
    }
  };

  return (
    <Space direction="vertical" size="large" className="full">
      <Card className="sectionCard">
        <div className="sectionHeader">
          <div>
            <Typography.Title level={4} className="sectionTitle">
              1. 创建任务并上传图片
            </Typography.Title>
            <Typography.Text className="sectionSubtitle">支持 PNG、JPG、JPEG，多张图片可在下一步组合为合并生成项。</Typography.Text>
          </div>
          <div className="actionBar">
            <Button className="btnPill btnPillDanger" danger onClick={clearWorkspace} disabled={generating || uploading}>
              一键清空
            </Button>
          </div>
        </div>
        <div className="uploadPanel">
          <Space direction="vertical" className="full">
            <Input
              className="prettyInput"
              placeholder="任务标题（可选），例如：5月证书问答批量生成"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
            <div className="actionRowCentered">
              <Upload
                className="uploadCenterCompact"
                multiple
                accept=".png,.jpg,.jpeg"
                beforeUpload={() => false}
                fileList={fileList}
                onChange={({ fileList: next }) => setFileList(next)}
                listType="picture"
              >
                <Tooltip overlayClassName="bigTooltip" title="先选择需要生成问答的图片（支持 PNG / JPG / JPEG，多张可后续合并生成）">
                  <Button size="large" className="btnPill btnPillSecondary">
                    选择图片
                  </Button>
                </Tooltip>
              </Upload>
            </div>
          </Space>
          <div className="toolbar mt">
            <div className="actionRowCentered full">
              <Tooltip overlayClassName="bigTooltip" title="创建任务并上传图片后，可在下一步填写描述并新增合并项。">
                <Button size="large" className="btnPill btnPillPrimary" type="primary" onClick={createAndUpload}>
                  创建任务并上传
                </Button>
              </Tooltip>
            </div>
          </div>
        </div>
      </Card>

      {images.length > 0 && (
        <Card
          className="sectionCard"
        >
          <div className="sectionHeader">
            <div>
              <Typography.Title level={4} className="sectionTitle">
                2. 填写描述并配置生成项
              </Typography.Title>
              <Typography.Text className="sectionSubtitle">单图项默认生成，合并项会额外生成新的问答草稿。</Typography.Text>
            </div>
            <Space className="actionBar">
              <Button size="middle" className="btnPill btnPillSecondary" onClick={createCombinedGenerationItem} disabled={selectedImageIds.size < 2}>
                新增合并项
              </Button>
              <Typography.Text type="secondary">已选择 {selectedImageIds.size} 张图片</Typography.Text>
            </Space>
          </div>
          <Typography.Paragraph type="secondary">
            如果证书、材料存在正反面或多张图片共同表达一个内容，可勾选多张图片新增合并项。合并项会和单图项一起参与 AI 生成，例如 1、2、3、4 之外可额外生成 13、34。
          </Typography.Paragraph>
          <Row gutter={[16, 16]} className="imageGrid">
            {images.map((item, index) => (
              <Col xs={24} md={12} lg={8} key={item.id}>
                <Card size="small" className="imageItemCard" title={`图片 ${index + 1}`}>
                  <Typography.Text strong>{item.original_name}</Typography.Text>
                  <Checkbox
                    checked={selectedImageIds.has(item.id)}
                    onChange={() =>
                      setSelectedImageIds((ids) => {
                        const next = new Set(ids);
                        if (next.has(item.id)) next.delete(item.id);
                        else next.add(item.id);
                        return next;
                      })
                    }
                  >
                    选择用于合并
                  </Checkbox>
                  <Image src={item.image_url} height={160} className="preview" />
                  <Input.TextArea
                    rows={4}
                    placeholder="请描述这张图片的业务含义、适用场景或希望生成问答的重点"
                    value={generationItems.find((generationItem) => !generationItem.is_combined && generationItem.image_ids[0] === item.id)?.description || ''}
                    onChange={(event) => {
                      const description = event.target.value;
                      setImages((current) => current.map((image) => (image.id === item.id ? { ...image, description } : image)));
                      setGenerationItems((current) =>
                        current.map((generationItem) =>
                          !generationItem.is_combined && generationItem.image_ids[0] === item.id ? { ...generationItem, description } : generationItem,
                        ),
                      );
                    }}
                  />
                </Card>
              </Col>
            ))}
          </Row>
          {generationItems.filter((item) => item.is_combined).length > 0 && (
            <div className="mergePanel">
              <Typography.Title level={5}>合并生成项</Typography.Title>
              <Typography.Paragraph type="secondary">这些项目会作为额外问答草稿参与生成，不会替代原来的单图项。</Typography.Paragraph>
              <Space direction="vertical" className="full">
                {generationItems
                  .filter((item) => item.is_combined)
                  .map((item) => (
                    <Card
                      size="small"
                      className="mergeItemCard"
                      key={item.id}
                      title={item.title}
                      extra={
                        <Button
                          size="middle"
                          className="btnPill btnPillSecondary"
                          onClick={() => setGenerationItems((current) => current.filter((generationItem) => generationItem.id !== item.id))}
                        >
                          移除
                        </Button>
                      }
                    >
                      <Typography.Paragraph type="secondary">
                        包含图片：{item.image_ids.map((id) => images.find((image) => image.id === id)?.original_name || id).join('、')}
                      </Typography.Paragraph>
                      <Input.TextArea
                        rows={4}
                        value={item.description}
                        placeholder="请描述这些图片合并后的业务含义，例如证书正反面共同说明的信息"
                        onChange={(event) =>
                          setGenerationItems((current) =>
                            current.map((generationItem) =>
                              generationItem.id === item.id ? { ...generationItem, description: event.target.value } : generationItem,
                            ),
                          )
                        }
                      />
                    </Card>
                  ))}
              </Space>
            </div>
          )}
          <div className="actionRowCentered mt">
            <Button
              size="large"
              className="btnPill btnPillPrimary"
              type="primary"
              loading={generating}
              disabled={uploading}
              onClick={saveDescriptionsAndGenerate}
            >
              保存描述并生成问答
            </Button>
          </div>
          <Typography.Paragraph className="mutedCenterText mb">
            建议先完善单图描述，再按需新增合并项；生成过程中可关闭弹窗继续其他操作。
          </Typography.Paragraph>
        </Card>
      )}

      <ProgressModal
        open={progressModalOpen}
        operation={activeOperation}
        progress={progress}
        onClose={() => setProgressModalOpen(false)}
      />

      {drafts.length > 0 && (
        <Card className="sectionCard">
          <div className="sectionHeader">
            <div>
              <Typography.Title level={4} className="sectionTitle">
                3. 审核和修改结果
              </Typography.Title>
              <Typography.Text className="sectionSubtitle">确认 AI 生成的问题、相似问法和答案，修改后可逐条保存。</Typography.Text>
            </div>
          </div>
          <DraftEditor
            drafts={drafts}
            setDrafts={setDrafts}
            markDirty={(id) => setDirtyDraftIds((ids) => new Set(ids).add(id))}
            clearDirty={(id) =>
              setDirtyDraftIds((ids) => {
                const next = new Set(ids);
                next.delete(id);
                return next;
              })
            }
          />
          <Form layout="vertical" className="mt">
            <Form.Item label="Webhook 链接" required>
              <Input value={webhookUrl} onChange={(event) => setWebhookUrl(event.target.value)} placeholder="https://qyapi.weixin.qq.com/..." />
            </Form.Item>
            <div className="actionRowCentered">
              <Button size="large" className="btnPill btnPillPrimary" type="primary" loading={uploading} disabled={generating} onClick={uploadWebhook}>
                上传到 webhook
              </Button>
            </div>
          </Form>
        </Card>
      )}

      {uploadRecords.length > 0 && (
        <Card className="dataCard" title="4. 本次上传记录">
          <Table
            className="resultTable"
            rowKey="id"
            dataSource={uploadRecords.filter((record) => record.batch === batch?.id)}
            columns={[
              { title: '问题', dataIndex: 'question' },
              { title: '状态', dataIndex: 'ok', render: (ok: boolean) => (ok ? '成功' : '失败') },
              { title: '企业微信记录', dataIndex: 'wechat_record_id' },
              { title: '图片 CDN 链接', dataIndex: 'image_cdn_urls', render: (urls: string[]) => urls.join('\n') },
              { title: '时间', dataIndex: 'created_at' },
            ]}
          />
        </Card>
      )}
    </Space>
  );
}

function useProgress(
  batchId: number | undefined,
  runKey: number,
  setProgress: (value: ProgressState) => void,
  onDone: (value: ProgressState) => void,
) {
  useEffect(() => {
    if (!batchId || runKey === 0) return undefined;
    let loadedDone = false;
    const load = async () => {
      const next = await api.getProgress(batchId);
      setProgress(next);
      if (['generated', 'completed', 'failed'].includes(next.status)) {
        window.clearInterval(timer);
        if (!loadedDone) {
          loadedDone = true;
          onDone(next);
        }
      }
    };
    const timer = window.setInterval(load, 2000);
    void load();
    return () => {
      window.clearInterval(timer);
    };
  }, [batchId, runKey]);
}

function ProgressModal({
  open,
  operation,
  progress,
  onClose,
}: {
  open: boolean;
  operation: 'generate' | 'webhook' | null;
  progress: ProgressState | null;
  onClose: () => void;
}) {
  const isDone = progress ? ['generated', 'completed', 'failed'].includes(progress.status) : false;
  const isFailed = progress?.status === 'failed';
  const title = operation === 'webhook' ? '正在上传 webhook' : '正在生成问答';
  const doneTitle = operation === 'webhook' ? 'Webhook 上传完成' : '问答生成完成';

  return (
    <Modal
      title={isDone && !isFailed ? doneTitle : title}
      open={open}
      closable={isDone}
      maskClosable={false}
      onCancel={isDone ? onClose : undefined}
      footer={
        isDone
          ? [
              <Button key="ok" type="primary" onClick={onClose}>
                知道了
              </Button>,
            ]
          : null
      }
    >
      <Space direction="vertical" className="full">
        <Progress percent={progress?.percent || 0} status={isFailed ? 'exception' : isDone ? 'success' : 'active'} />
        <Typography.Paragraph>{progress?.current_step || '任务已提交，正在准备...'}</Typography.Paragraph>
        <Typography.Text type={progress?.failed_count ? 'danger' : undefined}>
          已处理 {progress?.processed_count || 0}/{progress?.total_count || 0}，失败 {progress?.failed_count || 0}
        </Typography.Text>
        {progress?.error_message && <Typography.Paragraph type="danger">失败原因：{progress.error_message}</Typography.Paragraph>}
      </Space>
    </Modal>
  );
}

function DraftEditor({
  drafts,
  setDrafts,
  markDirty,
  clearDirty,
}: {
  drafts: FaqDraft[];
  setDrafts: (drafts: FaqDraft[]) => void;
  markDirty: (id: number) => void;
  clearDirty: (id: number) => void;
}) {
  const saveDraft = async (draft: FaqDraft) => {
    const saved = await api.updateDraft(draft);
    setDrafts(drafts.map((item) => (item.id === saved.id ? saved : item)));
    clearDirty(saved.id);
    message.success('已保存');
  };

  return (
    <List
      itemLayout="vertical"
      dataSource={drafts}
      renderItem={(draft, index) => (
        <List.Item>
          <Card className="draftItemCard">
          <Row gutter={[18, 18]}>
            <Col xs={24} md={8}>
              <div className="draftImageList">
              {(draft.generation_image_urls.length ? draft.generation_image_urls : draft.image?.image_url ? [draft.image.image_url] : []).map((url) => (
                <Image key={url} src={url} className="draftImage" />
              ))}
              {draft.generation_title && <Typography.Text type="secondary">生成项：{draft.generation_title}</Typography.Text>}
              </div>
            </Col>
            <Col xs={24} md={16}>
              <Space direction="vertical" className="full">
                <Typography.Text strong>主问题</Typography.Text>
                <Input
                  value={draft.question}
                  onChange={(event) => {
                    const next = [...drafts];
                    next[index] = { ...draft, question: event.target.value };
                    setDrafts(next);
                    markDirty(draft.id);
                  }}
                />
                <Typography.Text strong>相似问题</Typography.Text>
                <Input.TextArea
                  rows={4}
                  value={draft.similar_questions.join('\n')}
                  onChange={(event) => {
                    const next = [...drafts];
                    next[index] = { ...draft, similar_questions: event.target.value.split('\n').filter(Boolean) };
                    setDrafts(next);
                    markDirty(draft.id);
                  }}
                />
                <Typography.Text strong>答案</Typography.Text>
                <Input.TextArea
                  rows={5}
                  value={draft.answer_text}
                  onChange={(event) => {
                    const next = [...drafts];
                    next[index] = { ...draft, answer_text: event.target.value };
                    setDrafts(next);
                    markDirty(draft.id);
                  }}
                />
                <Button onClick={() => saveDraft(draft)}>保存当前修改</Button>
              </Space>
            </Col>
          </Row>
          </Card>
        </List.Item>
      )}
    />
  );
}

function BatchHistory() {
  const [batches, setBatches] = useState<BatchJob[]>([]);

  useEffect(() => {
    api.listBatches().then(setBatches).catch((error) => message.error(error.message));
  }, []);

  return (
    <Card className="dataCard">
      <div className="sectionHeader">
        <div>
          <Typography.Title level={4} className="sectionTitle">历史任务</Typography.Title>
          <Typography.Text className="sectionSubtitle">查看所有批量任务的状态、处理进度和创建时间。</Typography.Text>
        </div>
      </div>
      <Table
        rowKey="id"
        dataSource={batches}
        columns={[
          { title: 'ID', dataIndex: 'id' },
          { title: '标题', dataIndex: 'title' },
          { title: '状态', dataIndex: 'status' },
          { title: '图片数', dataIndex: 'image_count' },
          { title: '已处理', dataIndex: 'processed_count' },
          { title: '失败', dataIndex: 'failed_count' },
          { title: '创建时间', dataIndex: 'created_at' },
        ]}
      />
    </Card>
  );
}

function UploadRecords() {
  const [records, setRecords] = useState<UploadRecord[]>([]);

  useEffect(() => {
    api.listUploadRecords().then(setRecords).catch((error) => message.error(error.message));
  }, []);

  return (
    <Card className="dataCard">
      <div className="sectionHeader">
        <div>
          <Typography.Title level={4} className="sectionTitle">上传记录</Typography.Title>
          <Typography.Text className="sectionSubtitle">只保存企业微信返回的图片 CDN 链接，不保存 base64。</Typography.Text>
        </div>
      </div>
      <Table
        rowKey="id"
        dataSource={records}
        columns={[
          { title: '问题', dataIndex: 'question' },
          { title: '状态', dataIndex: 'ok', render: (ok: boolean) => (ok ? <span className="statusTextSuccess">成功</span> : <span className="statusTextDanger">失败</span>) },
          { title: '企业微信记录', dataIndex: 'wechat_record_id' },
          { title: 'CDN 链接', dataIndex: 'image_cdn_urls', render: (urls: string[]) => <span className="linkText">{urls.join('\n')}</span> },
          { title: '时间', dataIndex: 'created_at' },
        ]}
      />
    </Card>
  );
}

function TokenUsage() {
  const [usage, setUsage] = useState<LlmUsageSummary | null>(null);

  useEffect(() => {
    api.getLlmUsage().then(setUsage).catch((error) => message.error(error.message));
  }, []);

  if (!usage) return <Card className="dataCard">加载 Token 用量中...</Card>;

  return (
    <Space direction="vertical" size="large" className="full">
      <div className="sectionHeader">
        <div>
          <Typography.Title level={4} className="sectionTitle">Token 用量</Typography.Title>
          <Typography.Text className="sectionSubtitle">统计当前账号的大模型调用用量和最近调用明细。</Typography.Text>
        </div>
      </div>
      <Row gutter={[16, 16]} className="kpiGrid">
        <Col xs={24} md={8}>
          <Card className="kpiCard" title="输入 Token">
            <p className="kpiValue">{usage.prompt_tokens}</p>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="kpiCard" title="输出 Token">
            <p className="kpiValue">{usage.completion_tokens}</p>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="kpiCard" title="总 Token">
            <p className="kpiValue">{usage.total_tokens}</p>
          </Card>
        </Col>
      </Row>
      <Card className="dataCard" title="最近调用明细">
        <Table
          rowKey="id"
          dataSource={usage.items}
          columns={[
            { title: '模型', dataIndex: 'model' },
            { title: '问题', dataIndex: 'draft_question' },
            { title: '输入 Token', dataIndex: 'prompt_tokens' },
            { title: '输出 Token', dataIndex: 'completion_tokens' },
            { title: '总 Token', dataIndex: 'total_tokens' },
            { title: '状态', dataIndex: 'ok', render: (ok: boolean) => (ok ? '成功' : '失败') },
            { title: '时间', dataIndex: 'created_at' },
          ]}
        />
      </Card>
    </Space>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

