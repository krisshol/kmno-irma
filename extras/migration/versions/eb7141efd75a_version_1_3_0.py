"""version 1.3.0

Revision ID: eb7141efd75a
Revises: 430a70c8aa21
Create Date: 2016-01-06 13:38:46.918409

"""

# revision identifiers, used by Alembic.
revision = 'eb7141efd75a'
down_revision = '430a70c8aa21'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from frontend.models.sqlobjects import FileWeb
from lib.common.utils import UUID
from sqlalchemy.orm import sessionmaker, scoped_session


def upgrade():
    bind = op.get_bind()
    session = scoped_session(sessionmaker(autocommit=False, autoflush=False,
                                          bind=bind))
    op.add_column('irma_file', sa.Column('mimetype',
                                         sa.String(),
                                         nullable=True))
    op.add_column('irma_fileWeb', sa.Column('external_id',
                                            sa.String(length=36),
                                            nullable=True))
    op.add_column('irma_fileWeb', sa.Column('id_parent',
                                            sa.Integer(),
                                            nullable=True))
    op.add_column('irma_fileWeb', sa.Column('path',
                                            sa.String(length=255),
                                            nullable=True))

    # Create external_id as new uuid
    for fileweb in session.query(FileWeb).all():
        if fileweb.external_id is None:
            fileweb.external_id = UUID.generate()
    session.commit()
    # Now that all data are fixed set column to non nullable
    op.alter_column('irma_fileWeb', 'external_id', nullable=False)

    op.create_index(op.f('ix_irma_fileWeb_external_id'),
                    'irma_fileWeb',
                    ['external_id'],
                    unique=False)
    op.drop_constraint(u'irma_fileWeb_id_scan_scan_file_idx_key',
                       'irma_fileWeb',
                       type_='unique')
    op.create_unique_constraint(None,
                                'irma_fileWeb',
                                ['external_id'])
    op.create_foreign_key(None,
                          'irma_fileWeb',
                          'irma_file',
                          ['id_parent'],
                          ['id'])
    op.drop_column('irma_fileWeb', 'scan_file_idx')
    op.add_column('irma_scan', sa.Column('force',
                                         sa.Boolean(),
                                         nullable=True))
    op.add_column('irma_scan', sa.Column('mimetype_filtering',
                                         sa.Boolean(),
                                         nullable=True))
    op.add_column('irma_scan', sa.Column('probelist',
                                         sa.String(),
                                         nullable=True))
    op.add_column('irma_scan', sa.Column('resubmit_files',
                                         sa.Boolean(),
                                         nullable=True))
    op.add_column('irma_tag', sa.Column('text',
                                        sa.String(),
                                        nullable=False))
    op.drop_column('irma_tag', 'name')


def downgrade():
    bind = op.get_bind()
    session = scoped_session(sessionmaker(autocommit=False, autoflush=False,
                                          bind=bind))
    op.add_column('irma_tag', sa.Column('name',
                                        sa.VARCHAR(),
                                        autoincrement=False,
                                        nullable=False))
    op.drop_column('irma_tag', 'text')
    op.drop_column('irma_scan', 'resubmit_files')
    op.drop_column('irma_scan', 'probelist')
    op.drop_column('irma_scan', 'mimetype_filtering')
    op.drop_column('irma_scan', 'force')
    op.add_column('irma_fileWeb', sa.Column('scan_file_idx',
                                            sa.INTEGER(),
                                            autoincrement=False,
                                            nullable=True))

    # Create scan_file_idx autoincrement per scan
    last_id_scan = None
    scan_idx = 0
    for fileweb in session.query(FileWeb).all():
        if last_id_scan != fileweb.id_scan:
            last_id_scan = fileweb.id_scan
            scan_idx = 0
        if fileweb.scan_file_idx is None:
            fileweb.scan_file_idx = scan_idx
            scan_idx += 1
    # Now that all data are fixed set column to non nullable
    op.alter_column('irma_fileWeb', 'scan_file_idx', nullable=False)

    op.drop_constraint(None, 'irma_fileWeb', type_='foreignkey')
    op.drop_constraint(None, 'irma_fileWeb', type_='unique')
    op.create_unique_constraint(u'irma_fileWeb_id_scan_scan_file_idx_key',
                                'irma_fileWeb',
                                ['id_scan', 'scan_file_idx'])
    op.drop_index(op.f('ix_irma_fileWeb_external_id'),
                  table_name='irma_fileWeb')
    op.drop_column('irma_fileWeb', 'path')
    op.drop_column('irma_fileWeb', 'id_parent')
    op.drop_column('irma_fileWeb', 'external_id')
    op.drop_column('irma_file', 'mimetype')
